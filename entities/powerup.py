"""Floating power-ups: drift down, bob, magnetize slightly to player."""

import math
import random

from rendering import colors as C
from rendering.sprites import POWERUP_GLYPHS

KINDS = ["health", "shield", "energy", "rapid", "double", "bomb", "weapon"]
WEIGHTS = [18, 16, 14, 14, 10, 10, 12]
COLORS = {
    "health": C.BRIGHT_GREEN,
    "shield": C.SHIELD,
    "energy": C.BRIGHT_CYAN,
    "rapid": C.BRIGHT_YELLOW,
    "double": C.BRIGHT_MAGENTA,
    "bomb": C.BRIGHT_RED,
    "weapon": C.BRIGHT_WHITE,
    "life": C.BRIGHT_YELLOW,
}


class PowerUp:
    def __init__(self, x, y, kind=None):
        if kind is None:
            kind = random.choices(KINDS, weights=WEIGHTS)[0]
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.vy = 7.0
        self.t = 0.0
        glyph, _label = POWERUP_GLYPHS.get(kind, ("[?]", "?"))
        self.glyph = glyph
        self.label = _label

    def update(self, dt, player_x, player_y):
        self.t += dt
        # gentle magnet toward player when close
        dx, dy = player_x - self.x, player_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 14 and dist > 0.5:
            self.x += dx / dist * 10 * dt
            self.y += dy / dist * 6 * dt
        self.y += self.vy * dt
        self.x += math.sin(self.t * 3.0) * 4.0 * dt

    def draw(self, renderer):
        blink = (int(self.t * 6) % 2 == 0)
        col = COLORS.get(self.kind, C.POWERUP)
        if blink:
            col = C.BRIGHT_WHITE
        renderer.text(self.x - len(self.glyph) // 2, self.y, self.glyph, col)
