"""Lightweight pooled particle system.

Each particle: x, y, vx, vy, life, max_life, char, color, gravity.
Fixed pool (default 600) recycled oldest-first — no per-frame allocation
spikes. Used for engine exhaust, explosions, impacts, nova, pickups.
"""

import random

from rendering import colors as C

_CHARS = ["*", ".", "∙", "+", "x", "o", "'", "`", "·"]


class ParticleSystem:
    def __init__(self, max_particles=600):
        self.max = max_particles
        self.parts = []  # list of dicts

    def __len__(self):
        return len(self.parts)

    def clear(self):
        self.parts.clear()

    def spawn(self, x, y, vx=0.0, vy=0.0, life=0.5, char="*",
              color="", gravity=0.0):
        p = {
            "x": float(x), "y": float(y),
            "vx": float(vx), "vy": float(vy),
            "life": float(life), "max": float(life) if life > 0 else 1.0,
            "char": char, "color": color, "g": float(gravity),
        }
        if len(self.parts) >= self.max:
            # recycle oldest (index 0)
            self.parts.pop(0)
        self.parts.append(p)

    # ------------------------------------------------------------ presets
    def engine_exhaust(self, x, y):
        self.spawn(x + random.uniform(-0.6, 0.6), y,
                   vx=random.uniform(-2, 2), vy=random.uniform(10, 20),
                   life=random.uniform(0.15, 0.35),
                   char=random.choice(["|", ".", "'", "*"]),
                   color=random.choice([C.PLAYER_ENGINE, C.YELLOW, C.BRIGHT_WHITE]))

    def explosion(self, x, y, color="", count=26, power=26.0):
        for _ in range(count):
            ang = random.uniform(0, 6.2832)
            sp = random.uniform(power * 0.25, power)
            import math
            self.spawn(x, y,
                       vx=math.cos(ang) * sp, vy=math.sin(ang) * sp * 0.6,
                       life=random.uniform(0.3, 0.9),
                       char=random.choice(_CHARS),
                       color=color or random.choice(
                           [C.BRIGHT_YELLOW, C.YELLOW, C.ENEMY, C.BRIGHT_WHITE]))

    def sparks(self, x, y, color="", count=8):
        for _ in range(count):
            self.spawn(x + random.uniform(-1, 1), y + random.uniform(-0.5, 0.5),
                       vx=random.uniform(-18, 18), vy=random.uniform(-12, 12),
                       life=random.uniform(0.15, 0.4),
                       char=random.choice(["·", "'", "`", "."]),
                       color=color or C.BRIGHT_YELLOW)

    def pickup_burst(self, x, y, color=""):
        for _ in range(14):
            import math
            ang = random.uniform(0, 6.2832)
            sp = random.uniform(4, 14)
            self.spawn(x, y, vx=math.cos(ang) * sp, vy=math.sin(ang) * sp,
                       life=random.uniform(0.3, 0.6),
                       char=random.choice(["+", "*", "o"]),
                       color=color or C.POWERUP)

    def nova_ring(self, x, y, radius, color=""):
        import math
        n = max(12, int(radius * 2))
        for i in range(n):
            ang = (i / n) * 6.2832
            self.spawn(x + math.cos(ang) * radius, y + math.sin(ang) * radius * 0.55,
                       vx=math.cos(ang) * 22, vy=math.sin(ang) * 12,
                       life=random.uniform(0.4, 0.8),
                       char=random.choice(["*", "+", "o"]),
                       color=color or C.NOVA)

    def trail(self, x, y, color, char="·"):
        self.spawn(x, y, vx=random.uniform(-1, 1), vy=random.uniform(2, 6),
                   life=random.uniform(0.2, 0.45), char=char, color=color)

    # ------------------------------------------------------------- update
    def update(self, dt):
        if not self.parts:
            return
        alive = []
        for p in self.parts:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["vy"] += p["g"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            alive.append(p)
        # keep pool bounded without reallocating the list object excessively
        self.parts = alive[-self.max:]

    def draw(self, renderer):
        for p in self.parts:
            # fade: dim color in last third of life
            frac = p["life"] / p["max"] if p["max"] > 0 else 0
            col = p["color"]
            if frac < 0.33 and col in (C.BRIGHT_WHITE, C.BRIGHT_YELLOW):
                col = C.DIM + col
            renderer.put(p["x"], p["y"], p["char"], col)
