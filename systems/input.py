"""Non-blocking keyboard input for Windows (msvcrt) + Unix fallback.

Design: every frame the engine calls poll(dt), which drains the OS key
buffer and refreshes a `held` map with expiry timestamps. This emulates
key-hold (needed for smooth movement + simultaneous shooting) even though
msvcrt has no key-up events: a key stays "held" for HOLD_MS after its last
repeat event, and OS auto-repeat keeps refreshing it while physically held.

Exposes both `held` (continuous) and `pressed` (edge, this frame only).
"""

import sys
import time

HOLD_MS = 180

# Action names
LEFT = "left"
RIGHT = "right"
UP = "up"
DOWN = "down"
SHOOT = "shoot"
NOVA = "nova"
PAUSE = "pause"
QUIT = "quit"
CONFIRM = "confirm"
MUTE = "mute"
DEBUG = "debug"
MENU_UP = "menu_up"
MENU_DOWN = "menu_down"


class InputState:
    def __init__(self):
        self.held = set()
        self.pressed = set()

    def is_held(self, action):
        return action in self.held

    def was_pressed(self, action):
        return action in self.pressed


class InputSystem:
    def __init__(self):
        self.state = InputState()
        self._held_until = {}  # action -> perf_counter expiry
        self._on_windows = (sys.platform == "win32")
        self._msvcrt = None
        if self._on_windows:
            try:
                import msvcrt  # noqa: F401
                import msvcrt as _m
                self._msvcrt = _m
            except Exception:
                self._msvcrt = None
        # Unix fallback pieces (lazy import to avoid breaking Windows)
        self._unix_ready = False
        if not self._on_windows:
            self._setup_unix()

    # ------------------------------------------------------------- unix tty
    def _setup_unix(self):
        try:
            import termios  # type: ignore
            import tty  # type: ignore
            import select  # type: ignore
            self._termios = termios
            self._tty = tty
            self._select = select
            self._fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(self._fd)  # type: ignore
            tty.setcbreak(self._fd)  # type: ignore
            self._unix_ready = True
        except Exception:
            self._unix_ready = False

    def restore_unix(self):
        if not self._on_windows and self._unix_ready:
            try:
                self._termios.tcsetattr(self._fd, self._termios.TCSADRAIN,  # type: ignore
                                        self._old_settings)
            except Exception:
                pass

    # ---------------------------------------------------------------- poll
    def poll(self):
        pressed = set()
        now = time.perf_counter()
        if self._on_windows and self._msvcrt is not None:
            pressed = self._drain_msvcrt()
        elif not self._on_windows and self._unix_ready:
            pressed = self._drain_unix()
        # refresh hold timers
        for action in pressed:
            self._held_until[action] = now + HOLD_MS / 1000.0
        # expire
        held = {a for a, exp in self._held_until.items() if exp > now}
        # movement keys should linger slightly longer for smoothness
        self.state.held = held
        self.state.pressed = pressed
        return self.state

    # -------------------------------------------------------------- drains
    def _drain_msvcrt(self):
        pressed = set()
        m = self._msvcrt
        if m is None:
            return pressed
        try:
            while m.kbhit():  # type: ignore
                ch = m.getch()  # type: ignore
                if ch in (b"\x00", b"\xe0"):  # special key prefix (arrows, F-keys)
                    ch2 = m.getch() if m.kbhit() else b""  # type: ignore
                    code = (ch + ch2)
                    pressed.update(self._map_special(code))
                else:
                    pressed.update(self._map_byte(ch))
        except Exception:
            pass
        return pressed

    def _drain_unix(self):
        pressed = set()
        try:
            import select as _sel
            while _sel.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if not ch:
                    break
                if ch == "\x1b":  # escape sequence?
                    seq = ch
                    # read up to 2 more chars non-blocking
                    while _sel.select([sys.stdin], [], [], 0)[0] and len(seq) < 3:
                        seq += sys.stdin.read(1)
                    pressed.update(self._map_ansi(seq))
                    if seq == "\x1b":
                        pressed.add(QUIT)
                else:
                    pressed.update(self._map_char(ch))
        except Exception:
            pass
        return pressed

    # --------------------------------------------------------------- maps
    def _map_byte(self, ch: bytes):
        try:
            if ch == b" ":
                return {SHOOT, CONFIRM}
            if ch in (b"\r", b"\n"):
                return {CONFIRM}
            if ch == b"\x1b":  # ESC
                return {QUIT, PAUSE}
            if ch == b"\t":
                return {NOVA}
            c = ch.decode("utf-8", errors="ignore").lower()
            return self._map_char(c)
        except Exception:
            return set()

    def _map_char(self, c: str):
        c = c.lower()
        if c in ("a", "A"):
            return {LEFT}
        if c in ("d", "D"):
            return {RIGHT}
        if c in ("w", "W"):
            return {UP, MENU_UP}
        if c in ("s", "S"):
            return {DOWN, MENU_DOWN}
        if c == " ":
            return {SHOOT, CONFIRM}
        if c in ("x", "b", "e", "q", "f"):
            # X/B primary nova; E/Q/F aliases (Shift not detectable alone)
            return {NOVA}
        if c in ("p",):
            return {PAUSE}
        if c in ("r", "R"):
            return {CONFIRM}  # fast retry / confirm (game-over, menus)
        if c in ("m",):
            return {MUTE}
        if c in ("`", "0") or c == "\x7f":
            return {DEBUG}
        if c in ("\r", "\n"):
            return {CONFIRM}
        return set()

    def _map_special(self, code: bytes):
        # msvcrt arrow codes: \xe0H up, \xe0P down, \xe0K left, \xe0M right
        if code in (b"\xe0H", b"\x00H"):
            return {UP, MENU_UP}
        if code in (b"\xe0P", b"\x00P"):
            return {DOWN, MENU_DOWN}
        if code in (b"\xe0K", b"\x00K"):
            return {LEFT}
        if code in (b"\xe0M", b"\x00M"):
            return {RIGHT}
        if code in (b"\xe0;", b"\x00;"):  # F1-ish
            return {DEBUG}
        return set()

    def _map_ansi(self, seq: str):
        if seq in ("\x1b[A",):
            return {UP, MENU_UP}
        if seq in ("\x1b[B",):
            return {DOWN, MENU_DOWN}
        if seq in ("\x1b[C",):
            return {RIGHT}
        if seq in ("\x1b[D",):
            return {LEFT}
        return set()
