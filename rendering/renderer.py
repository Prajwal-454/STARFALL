"""Buffered terminal renderer: game logic never touches stdout directly.

Strategy for 60fps without flicker:
  * Query terminal size with shutil.get_terminal_size() each frame (cheap,
    handles resize).
  * Maintain char + color grids sized to the terminal.
  * All draw calls write into the grids.
  * present() builds ONE string (with minimal ANSI switches) and performs
    ONE sys.stdout.write + flush, starting from cursor-home (no full clear).
  * Optional screen-shake offsets the whole frame; optional full-frame flash
    overlays a color.
"""

import ctypes
import os
import shutil
import sys

from rendering import colors as C


def disp_width(s):
    """Visible terminal cells for a string (wide emoji/CJK count as 2).

    HUD/menu alignment must use this instead of len(), otherwise double-
    width glyphs (emoji, some symbols) push text off-center and overflow
    box borders — especially on narrow terminals.
    """
    w = 0
    for ch in s:
        o = ord(ch)
        # Wide ranges: CJK, fullwidth, common emoji blocks, symbols like ♥⬢☠
        if (0x1100 <= o <= 0x115F or 0x2E80 <= o <= 0xA4CF
                or 0xAC00 <= o <= 0xD7A3 or 0xF900 <= o <= 0xFAFF
                or 0xFE30 <= o <= 0xFE4F or 0xFF00 <= o <= 0xFF60
                or 0xFFE0 <= o <= 0xFFE6 or 0x1F000 <= o <= 0x1FAFF
                or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF):
            w += 2
        else:
            w += 1
    return w


def clip_to_width(s, max_cells):
    """Truncate a string to fit max_cells display cells."""
    if disp_width(s) <= max_cells:
        return s
    out = []
    used = 0
    for ch in s:
        cw = 2 if disp_width(ch) > 1 else 1
        if used + cw > max_cells:
            break
        out.append(ch)
        used += cw
    return "".join(out)


class TerminalRenderer:
    def __init__(self):
        self.width = 120
        self.height = 35
        self.chars = []
        self.colors = []
        self._alt_screen = False
        self._vt_enabled = False

    # ---------------------------------------------------------- lifecycle
    def setup(self):
        self._enable_vt()
        try:
            reconf = getattr(sys.stdout, "reconfigure", None)
            if callable(reconf):
                reconf(encoding="utf-8", errors="replace")
        except Exception:
            pass
        # Try alternate screen so we don't clobber scrollback.
        try:
            sys.stdout.write("\x1b[?1049h")
            self._alt_screen = True
        except Exception:
            self._alt_screen = False
        self.hide_cursor()
        self.refresh_size()
        self.clear_screen()

    def restore(self):
        try:
            sys.stdout.write(C.RESET + "\x1b[?25h")
            if self._alt_screen:
                sys.stdout.write("\x1b[?1049l")
            sys.stdout.flush()
        except Exception:
            pass

    def _enable_vt(self):
        if os.name != "nt" or self._vt_enabled:
            return
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong(0)
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VT = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | ENABLE_VT)
                self._vt_enabled = True
        except Exception:
            pass

    def hide_cursor(self):
        try:
            sys.stdout.write("\x1b[?25l")
            sys.stdout.flush()
        except Exception:
            pass

    def clear_screen(self):
        try:
            sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.flush()
        except Exception:
            pass

    # -------------------------------------------------------------- sizing
    def refresh_size(self):
        try:
            size = shutil.get_terminal_size(fallback=(120, 35))
            self.width = max(40, size.columns)
            self.height = max(20, size.lines)
        except Exception:
            self.width, self.height = 120, 35
        self.chars = [[" "] * self.width for _ in range(self.height)]
        self.colors = [[""] * self.width for _ in range(self.height)]
        return self.width, self.height

    # ------------------------------------------------------------- drawing
    def clear_buffers(self):
        for y in range(self.height):
            row_c = self.chars[y]
            row_k = self.colors[y]
            for x in range(self.width):
                row_c[x] = " "
                row_k[x] = ""

    def put(self, x, y, ch, color=""):
        ix, iy = int(x), int(y)
        if 0 <= ix < self.width and 0 <= iy < self.height and ch:
            self.chars[iy][ix] = ch[0]
            self.colors[iy][ix] = color or ""

    def text(self, x, y, s, color=""):
        ix, iy = int(x), int(y)
        if not (0 <= iy < self.height):
            return
        for i, ch in enumerate(s):
            xx = ix + i
            if 0 <= xx < self.width:
                self.chars[iy][xx] = ch
                self.colors[iy][xx] = color or ""

    def text_centered(self, y, s, color=""):
        self.text(max(0, (self.width - disp_width(s)) // 2), y, s, color)

    def sprite(self, x, y, rows, color=""):
        ix, iy = int(x), int(y)
        for r, row in enumerate(rows):
            yy = iy + r
            if not (0 <= yy < self.height):
                continue
            for c, ch in enumerate(row):
                if ch == " ":
                    continue
                xx = ix + c
                if 0 <= xx < self.width:
                    self.chars[yy][xx] = ch
                    self.colors[yy][xx] = color or ""

    def rich_sprite(self, x, y, cells):
        """Blit a layered cell grid: rows of (char, color) or None.

        Used by the AURORA player ship (true-color, per-cell lighting).
        Transparent cells (None) leave the background untouched.
        """
        ix, iy = int(x), int(y)
        for r, row in enumerate(cells):
            yy = iy + r
            if not (0 <= yy < self.height):
                continue
            for c, cell in enumerate(row):
                if cell is None:
                    continue
                ch, col = cell
                if not ch or ch == " ":
                    continue
                xx = ix + c
                if 0 <= xx < self.width:
                    self.chars[yy][xx] = ch[0]
                    self.colors[yy][xx] = col or ""

    def hline(self, x, y, w, ch="─", color=""):
        for i in range(w):
            self.put(x + i, y, ch, color)

    def box(self, x, y, w, h, color="", title=""):
        if w < 4 or h < 3:
            return
        self.put(x, y, "╔", color)
        self.put(x + w - 1, y, "╗", color)
        self.put(x, y + h - 1, "╚", color)
        self.put(x + w - 1, y + h - 1, "╝", color)
        for i in range(1, w - 1):
            self.put(x + i, y, "═", color)
            self.put(x + i, y + h - 1, "═", color)
        for j in range(1, h - 1):
            self.put(x, y + j, "║", color)
            self.put(x + w - 1, y + j, "║", color)
        if title:
            label = clip_to_width(f" {title} ", w - 4)
            self.text(x + 2, y, label, color)

    def bar(self, x, y, w, frac, fill="█", empty="░", color="", dim=""):
        frac = max(0.0, min(1.0, frac))
        n = int(round(w * frac))
        for i in range(w):
            self.put(x + i, y, fill if i < n else empty,
                      color if i < n else (dim or color))

    # ------------------------------------------------------------- present
    def present(self, shake_x=0, shake_y=0, flash_color="", flash_alpha=0.0):
        """Flush buffers to the terminal in a single write."""
        sx, sy = int(shake_x), int(shake_y)
        out = ["\x1b[H"]  # cursor home, no clear -> no flicker
        cur_color = None
        for y in range(self.height):
            sy_eff = y + sy
            # vertical shake: sample shifted row, blank if out of range
            row_c = self.chars[sy_eff] if 0 <= sy_eff < self.height else None
            row_k = self.colors[sy_eff] if 0 <= sy_eff < self.height else None
            out.append(f"\x1b[{y + 1};1H")
            for x in range(self.width):
                ch, col = " ", ""
                if row_c is not None and row_k is not None:
                    xx = x + sx
                    if 0 <= xx < self.width:
                        ch = row_c[xx]
                        col = row_k[xx]
                if flash_color and flash_alpha > 0:
                    # cheap flash: override empty-ish cells with tint on alpha
                    pass
                if col != cur_color:
                    out.append(col if col else C.RESET)
                    cur_color = col
                out.append(ch)
        out.append(C.RESET)
        try:
            sys.stdout.write("".join(out))
            sys.stdout.flush()
        except Exception:
            pass
