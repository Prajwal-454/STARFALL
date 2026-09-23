"""Structured wave spawner: formations, not random scatter.

Waves 1..N are data-driven compositions with spawn patterns:
  line, v, sides, swarm, snake, escort.
Boss waves (every 5th, plus WIN_WAVE) spawn a Boss instead.
After WIN_WAVE the game continues in endless mode with scaling.
"""

import random

FORMATIONS = ["line", "v", "sides", "swarm", "snake"]

WAVE_TABLE = {
    1: [("fighter", 5)],
    2: [("fighter", 8), ("interceptor", 2)],
    3: [("fighter", 6), ("interceptor", 3), ("tank", 1)],
    4: [("fighter", 8), ("bomber", 2), ("interceptor", 3)],
    5: [("boss", 1)],
    6: [("fighter", 8), ("elite", 2), ("tank", 2)],
    7: [("interceptor", 6), ("bomber", 3), ("tank", 2)],
    8: [("elite", 3), ("fighter", 10), ("bomber", 2)],
    9: [("tank", 4), ("elite", 3), ("interceptor", 5)],
    10: [("boss", 1)],
    11: [("boss", 1)],  # final boss -> victory
}


def composition_for(wave):
    if wave in WAVE_TABLE:
        return WAVE_TABLE[wave]
    # endless scaling beyond table
    n_f = min(14, 6 + wave // 2)
    n_i = min(8, wave // 2)
    n_t = min(5, wave // 3)
    n_e = min(5, (wave - 6) // 2)
    comp = [("fighter", n_f), ("interceptor", n_i), ("tank", n_t)]
    if n_e > 0:
        comp.append(("elite", n_e))
    if wave % 5 == 0:
        comp.append(("boss", 1))
    return comp


class WaveManager:
    def __init__(self):
        self.wave = 0
        self.queue = []  # list of (time_left, kind)
        self.spawn_timer = 0.0
        self.wave_active = False
        self.wave_clear_timer = 0.0
        self.between_waves = True
        self.intermission = 2.0
        self.formation = "line"

    def start_wave(self, n):
        self.wave = n
        self.formation = random.choice(FORMATIONS)
        comp = composition_for(n)
        self.queue = []
        t = 0.5
        for kind, count in comp:
            if kind == "boss":
                continue  # engine spawns boss directly
            for _ in range(count):
                self.queue.append([t, kind])
                t += random.uniform(0.35, 0.8)
        random.shuffle(self.queue)
        # keep rough formation ordering: sort half by time so groups arrive
        self.queue.sort(key=lambda e: e[0])
        self.wave_active = True
        self.between_waves = False

    def has_boss(self, n=None):
        n = self.wave if n is None else n
        return any(k == "boss" for k, _ in composition_for(n))

    def is_boss_wave(self, n=None):
        return self.has_boss(n)

    def update(self, dt, enemies_alive, boss_alive):
        """Return list of kinds to spawn this frame."""
        spawns = []
        if self.between_waves:
            self.intermission -= dt
            if self.intermission <= 0:
                self.start_wave(self.wave + 1)
                return ["__wave_started__"]
            return spawns
        # tick queue
        for item in self.queue:
            item[0] -= dt
        ready = [item for item in self.queue if item[0] <= 0]
        self.queue = [item for item in self.queue if item[0] > 0]
        for _, kind in ready:
            spawns.append(kind)
        # wave cleared?
        if not self.queue and enemies_alive == 0 and not boss_alive:
            self.wave_clear_timer += dt
            if self.wave_clear_timer > 1.2:
                self.wave_clear_timer = 0.0
                self.between_waves = True
                self.intermission = 3.0
                spawns.append("__wave_cleared__")
        else:
            self.wave_clear_timer = 0.0
        return spawns

    def spawn_x(self, w, i=0, n=1):
        """Formation-aware x position for the i-th of n spawns."""
        margin = 6
        if self.formation == "line":
            return random.uniform(margin, w - margin)
        if self.formation == "v":
            cx = w / 2
            off = (i - n / 2) * 8
            return max(margin, min(w - margin, cx + off))
        if self.formation == "sides":
            side = -1 if i % 2 == 0 else 1
            return margin + 4 if side < 0 else w - margin - 4
        if self.formation == "swarm":
            return w / 2 + random.uniform(-16, 16)
        # snake
        return w / 2 + (12 if i % 2 == 0 else -12)
