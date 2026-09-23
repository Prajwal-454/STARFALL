"""Score, combo, and floating combat text."""

import time


class ScoreSystem:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.best_combo = 0
        self.floaters = []  # {x,y,text,color,life,max}

    def add_kill(self, base, x, y):
        # combo window 3.5s; multiplier grows every 4 combo
        if self.combo_timer > 0:
            self.combo += 1
        else:
            self.combo = 1
        self.combo_timer = 3.5
        self.best_combo = max(self.best_combo, self.combo)
        # multiplier grows every 4 chain, hard-capped at x5 (fair, readable)
        mult = min(5.0, 1.0 + (self.combo // 4) * 0.5)
        gained = int(base * mult)
        self.score += gained
        label = f"+{gained}"
        if self.combo >= 4:
            label += f" x{self.combo}"
        color = "\x1b[93m" if self.combo >= 8 else "\x1b[97m"
        self.float_text(x, y - 2, label, color)
        return gained

    def add_bonus(self, amount, x, y, label="BONUS"):
        self.score += amount
        self.float_text(x, y - 2, f"{label} +{amount}", "\x1b[92m")

    def float_text(self, x, y, text, color=""):
        self.floaters.append({"x": float(x), "y": float(y), "text": text,
                              "color": color, "life": 1.1, "max": 1.1})

    def update(self, dt):
        self.combo_timer = max(0.0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo = 0
        alive = []
        for f in self.floaters:
            f["life"] -= dt
            f["y"] -= 6 * dt
            if f["life"] > 0:
                alive.append(f)
        self.floaters = alive[-40:]

    def draw(self, renderer):
        from rendering.renderer import disp_width
        for f in self.floaters:
            a = f["life"] / f["max"]
            col = f["color"] if a > 0.35 else "\x1b[2m"
            renderer.text(f["x"] - disp_width(f["text"]) / 2, f["y"], f["text"], col)
