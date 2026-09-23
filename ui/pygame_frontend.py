"""Pygame GUI frontend for STARFALL — launch from CMD with: python main_gui.py.

Architecture: the game logic never touches the terminal directly. It only
calls the renderer API (put/text/sprite/rich_sprite/box/bar/present) and
input API (poll() -> InputState). So this file just re-implements those two
interfaces on top of pygame:

  PygameRenderer(TerminalRenderer) — reuses ALL grid logic (put, text,
      sprite, box, bar, alignment), only present() is overridden to draw
      cell rects + glyphs instead of ANSI strings.
  PygameInput — poll() returns the same InputState (held/pressed action
      names) built from real key-down/up events, no expiry hacks needed.

Logical grid stays 120x35 cells so gameplay, HUD layout and collision are
identical to the terminal version — only the pixels change.
"""

import pygame

from rendering import colors as C
from rendering.renderer import TerminalRenderer
from systems.input import (CONFIRM, DEBUG, DOWN, LEFT, MUTE, NOVA, PAUSE,
                           QUIT, RIGHT, SHOOT, UP, InputState)

CELL_W, CELL_H = 8, 16
GRID_W, GRID_H = 120, 35

# Standard 16-color RGB (VGA-ish) for the ANSI palette in rendering/colors.
ANSI_RGB = {
    30: (12, 12, 12), 31: (197, 15, 31), 32: (19, 161, 14),
    33: (193, 156, 0), 34: (0, 55, 218), 35: (136, 23, 152),
    36: (58, 150, 221), 37: (204, 204, 204),
    90: (118, 118, 118), 91: (231, 72, 86), 92: (22, 198, 12),
    93: (249, 241, 165), 94: (59, 120, 255), 95: (180, 0, 158),
    96: (97, 214, 214), 97: (242, 242, 242),
}

BLOCKS = set("█▓▒░▄▀")  # drawn as fast filled rects (crisp pixel-art look)


def ansi_to_rgb(seq):
    """Parse an ANSI color string (possibly concatenated codes + truecolor)
    into an (r, g, b) tuple. Unknown/empty -> white."""
    if not seq:
        return (242, 242, 242)
    # collect all numeric SGR params in order, e.g. "38;2;r;g;b", "1", "91"
    nums = []
    for chunk in seq.replace("\x1b[", ";").split(";"):
        chunk = chunk.strip("m ").strip()
        if not chunk:
            continue
        try:
            nums.append(int(chunk))
        except Exception:
            pass
    rgb = None
    bold = False
    dim = False
    i = 0
    while i < len(nums):
        n = nums[i]
        if n == 38 and i + 4 < len(nums) and nums[i + 1] == 2:
            rgb = (nums[i + 2], nums[i + 3], nums[i + 4])
            i += 5
        elif n == 1:
            bold = True
            i += 1
        elif n == 2:
            dim = True
            i += 1
        else:
            rgb = ANSI_RGB.get(n, rgb)
            i += 1
    if rgb is None:
        rgb = (242, 242, 242)
    if dim:
        rgb = tuple(int(v * 0.55) for v in rgb)
    elif bold:
        rgb = tuple(min(255, int(v * 1.15) + 12) for v in rgb)
    return rgb


class PygameRenderer(TerminalRenderer):
    def __init__(self):
        super().__init__()
        self.width, self.height = GRID_W, GRID_H
        self.screen = None
        self.font = None
        self._glyph_cache = {}

    def setup(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (GRID_W * CELL_W, GRID_H * CELL_H))
        pygame.display.set_caption("STARFALL: TERMINAL WAR (GUI)")
        try:
            self.font = pygame.font.SysFont("consolas", 14)
        except Exception:
            self.font = None  # type: ignore
        if self.font is None:
            self.font = pygame.font.Font(None, 14)
        assert self.font is not None
        self.refresh_size()

    def restore(self):
        try:
            pygame.quit()
        except Exception:
            pass

    def refresh_size(self):
        self.width, self.height = GRID_W, GRID_H
        self.chars = [[" "] * self.width for _ in range(self.height)]
        self.colors = [[""] * self.width for _ in range(self.height)]
        return self.width, self.height

    def _glyph(self, ch, rgb):
        key = (ch, rgb)
        s = self._glyph_cache.get(key)
        if s is None:
            font = self.font
            assert font is not None, "PygameRenderer.setup() must run first"
            s = font.render(ch, True, rgb)
            # cache bounded: HUD + sprites use a small char/color set
            if len(self._glyph_cache) < 2000:
                self._glyph_cache[key] = s
        return s

    def present(self, shake_x=0, shake_y=0, flash_color="", flash_alpha=0.0):
        if self.screen is None:
            return
        self.screen.fill((5, 8, 18))  # deep-space background
        ox, oy = int(shake_x * CELL_W), int(shake_y * CELL_H)
        for y in range(self.height):
            for x in range(self.width):
                ch = self.chars[y][x]
                if not ch or ch == " ":
                    continue
                rgb = ansi_to_rgb(self.colors[y][x])
                px, py = x * CELL_W + ox, y * CELL_H + oy
                if ch in BLOCKS:
                    self.screen.fill(rgb, (px, py, CELL_W, CELL_H))
                else:
                    g = self._glyph(ch, rgb)
                    self.screen.blit(g, (px, py))
        pygame.display.flip()


_KEYMAP = {
    pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
    pygame.K_UP: UP, pygame.K_w: UP,
    pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_SPACE: SHOOT,
    pygame.K_x: NOVA, pygame.K_b: NOVA, pygame.K_TAB: NOVA,
    pygame.K_p: PAUSE,
    pygame.K_ESCAPE: QUIT,
    pygame.K_RETURN: CONFIRM, pygame.K_KP_ENTER: CONFIRM, pygame.K_r: CONFIRM,
    pygame.K_m: MUTE,
    pygame.K_F1: DEBUG, pygame.K_BACKQUOTE: DEBUG,
}


class PygameInput:
    """Same poll() -> InputState contract as systems/input.py."""

    def __init__(self):
        self.closed = False
        self._held = set()

    def poll(self):
        st = InputState()
        pressed = set()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.closed = True
            elif ev.type in (pygame.WINDOWFOCUSLOST,):
                self._held.clear()  # never stick keys on alt-tab
            elif ev.type == pygame.KEYDOWN:
                act = _KEYMAP.get(ev.key)
                if act:
                    self._held.add(act)
                    pressed.add(act)
            elif ev.type == pygame.KEYUP:
                act = _KEYMAP.get(ev.key)
                if act:
                    self._held.discard(act)
        # A key pressed this frame counts as held this frame (matches the
        # terminal frontend's hold-expiry feel, so quick taps still fire).
        self._held.update(pressed)
        try:
            keys = pygame.key.get_pressed()
            if not keys[pygame.K_SPACE] and SHOOT not in pressed:
                self._held.discard(SHOOT)
        except Exception:
            pass
        st.held = set(self._held)
        st.pressed = pressed
        return st

    def restore_unix(self):
        pass
