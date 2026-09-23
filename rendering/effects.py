"""Full-screen polish effects: shake, flash, announcements, starfield.

Starfield implements a 3-layer parallax: each star has depth (speed,
brightness, glyph). Stars drift downward to fake forward flight.
"""

import random

from rendering import colors as C


class ScreenShake:
    def __init__(self):
        self.trauma = 0.0

    def add(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt):
        self.trauma = max(0.0, self.trauma - dt * 1.6)

    def offset(self):
        mag = self.trauma * self.trauma * 3.0
        if mag < 0.05:
            return 0, 0
        return (random.uniform(-mag, mag), random.uniform(-mag, mag))


class DamageFlash:
    def __init__(self):
        self.timer = 0.0
        self.duration = 0.12

    def trigger(self):
        self.timer = self.duration

    def update(self, dt):
        self.timer = max(0.0, self.timer - dt)

    @property
    def active(self):
        return self.timer > 0


class Announcement:
    """Big centered banner text with fade in/out (wave, warning, etc.)."""

    def __init__(self):
        self.main = ""
        self.sub = ""
        self.timer = 0.0
        self.duration = 0.0
        self.color = C.BRIGHT_YELLOW

    def show(self, main, sub="", duration=2.2, color=""):
        self.main = main
        self.sub = sub
        self.timer = duration
        self.duration = duration
        self.color = color or C.BRIGHT_YELLOW

    def update(self, dt):
        self.timer = max(0.0, self.timer - dt)

    @property
    def active(self):
        return self.timer > 0

    @property
    def alpha(self):
        if self.duration <= 0:
            return 0.0
        t = self.timer / self.duration
        # fade in first 15%, out last 40%
        if t > 0.85:
            return (1.0 - t) / 0.15
        if t < 0.4:
            return t / 0.4
        return 1.0

    def draw(self, renderer, cy):
        if not self.active or self.alpha <= 0.05:
            return
        blink = "" if self.alpha > 0.5 else C.DIM
        renderer.text_centered(cy, f"── {self.main} ──", blink + self.color)
        if self.sub:
            renderer.text_centered(cy + 1, self.sub, C.HUD_TEXT)


class Starfield:
    """3 parallax layers of stars drifting downward."""

    GLYPHS = [".", "·", ".", "*", "✦", "✧", "+", "∙"]

    def __init__(self):
        self.stars = []  # dicts: x,y,speed,glyph,color,layer
        self.w = 120
        self.h = 35

    def resize(self, w, h, top_reserved=7):
        self.w, self.h = w, h
        # keep stars in bounds
        for s in self.stars:
            s["x"] = min(s["x"], w - 1)
            s["y"] = min(max(s["y"], top_reserved), h - 1)

    def init_stars(self, w, h, count=110, top_reserved=7):
        self.w, self.h = w, h
        self.stars = []
        for _ in range(count):
            layer = random.choice([0, 0, 1, 1, 2])  # bias to far layers
            if layer == 0:
                speed, glyph, color = random.uniform(2, 5), random.choice("·.∙"), C.STAR_DIM
            elif layer == 1:
                speed, glyph, color = random.uniform(6, 12), random.choice(".·+*"), C.STAR_MID
            else:
                speed, glyph, color = random.uniform(14, 26), random.choice("*✦✧"), C.STAR_BRIGHT
            self.stars.append({
                "x": random.uniform(0, w - 1),
                "y": random.uniform(top_reserved, h - 1),
                "speed": speed, "glyph": glyph, "color": color,
            })

    def update(self, dt, top_reserved=7, speed_mult=1.0, warp=False):
        mult = speed_mult * (3.2 if warp else 1.0)
        for s in self.stars:
            s["y"] += s["speed"] * mult * dt
            if warp and random.random() < dt * 8:
                s["x"] += random.uniform(-4, 4) * dt
            if s["y"] >= self.h:
                s["y"] = top_reserved + random.uniform(0, 1.5)
                s["x"] = random.uniform(0, self.w - 1)

    def draw(self, renderer):
        for s in self.stars:
            renderer.put(s["x"], s["y"], s["glyph"], s["color"])
