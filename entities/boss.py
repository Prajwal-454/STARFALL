"""Dreadnought boss: multi-phase, patterns, minion spawns, telegraphs.

Phases by hp fraction:
  P1 (>66%): aimed bursts + slow drift
  P2 (33-66%): radial rings + minion spawns
  P3 (<33%): enraged spiral + charge dives + wall patterns
"""

import math
import random

from game import config as CFG
from rendering import colors as C
from rendering import enemies_art as EA


class Boss:
    def __init__(self, x, y, wave=5, final=False):
        scale = 1.0 + (wave - 5) * 0.12
        self.x = float(x)
        self.y = float(y)
        self.target_y = 12.0
        self.max_hp = (900.0 if not final else 1400.0) * (1.0 + (wave - 5) * 0.15)
        self.hp = self.max_hp
        self.wave = wave
        self.final = final
        self.t = 0.0
        self.phase = 1
        self.fire_timer = 1.2
        self.ring_timer = 2.0
        self.minion_timer = 4.0
        self.charge_timer = 6.0
        self.charging = 0.0
        self.charge_vx = 0.0
        self.vx = 8.0
        self.flash = 0.0
        self.muzzle = 0.0  # main-cannon firing flash
        self.last_phase = 1  # engine watches for phase-change FX
        self.entering = True
        self.radius = 11.0
        self.score = CFG.SCORES["boss"] + (5000 if final else 0)
        self.name = "OBLIVION PRIME" if final else "DREADNOUGHT"
        self._scale = scale

    @property
    def frac(self):
        return max(0.0, self.hp / self.max_hp)

    def update_phase(self):
        if self.frac > 0.66:
            self.phase = 1
        elif self.frac > 0.33:
            self.phase = 2
        else:
            self.phase = 3

    def update(self, dt, player_x, field_w):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.fire_timer -= dt
        self.ring_timer -= dt
        self.minion_timer -= dt
        self.charge_timer -= dt
        self.update_phase()
        # entrance: descend to target_y
        if self.entering:
            self.y += 8.0 * dt
            if self.y >= self.target_y:
                self.entering = False
            return "entering"
        # charge attack in P3
        if self.charging > 0:
            self.charging -= dt
            self.x += self.charge_vx * dt
            self.y += 14.0 * dt
            if self.charging <= 0 or self.y > 26:
                self.charging = 0
                self.y = min(self.y, self.target_y)
            return None
        # normal drift: sine sweep
        speed = 10.0 + self.phase * 4.0
        self.x += math.sin(self.t * 0.7) * speed * dt
        self.x = max(16, min(field_w - 16, self.x))
        self.y += math.sin(self.t * 1.7) * 2.0 * dt
        if self.phase == 3 and self.charge_timer <= 0:
            # telegraph a charge dive toward the player
            self.charging = 1.1
            dx = player_x - self.x
            self.charge_vx = max(-30, min(30, dx * 3.0))
            self.charge_timer = random.uniform(5.0, 7.5)
            return "charge"
        return None

    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 0.1
        self.update_phase()
        return self.hp <= 0

    # --------------------------------------------------------------- events
    def want_aimed(self):
        interval = [1.1, 0.85, 0.55][self.phase - 1]
        if self.fire_timer <= 0 and not self.entering:
            self.fire_timer = interval
            return True
        return False

    def want_ring(self):
        if self.phase >= 2 and self.ring_timer <= 0 and not self.entering:
            self.ring_timer = 3.4 if self.phase == 2 else 2.4
            return True
        return False

    def want_minion(self):
        if self.phase >= 2 and self.minion_timer <= 0 and not self.entering:
            self.minion_timer = 5.0 if self.phase == 2 else 3.6
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, renderer):
        w, h = EA.dims("boss")
        x0 = self.x - w / 2
        y0 = self.y - h / 2
        phase = int(self.t * 4) % 2
        rage = self.phase >= 3
        # animation priority: hit-flash > charge dive > firing > telegraphs
        if self.flash > 0:
            variant = "dmg"
        elif self.charging > 0:
            variant = "warn" if int(self.t * 16) % 2 == 0 else "idle"
        elif self.muzzle > 0:
            variant = "shoot"
        elif self.ring_timer < 0.7 and self.phase >= 2 and not self.entering:
            variant = "charge"  # core charging telegraph before ring burst
        elif 0 < self.fire_timer < 0.35 and not self.entering:
            variant = "charge"  # laser buildup: break off or brace
        else:
            variant = "idle"
        EA.draw_flames_up(renderer, self.x, y0 - 1, int(self.t * 8), "boss")
        renderer.rich_sprite(x0, y0, EA.body_frame("boss", variant, phase, rage))
        if self.muzzle > 0:
            EA.draw_muzzle_down(renderer, self.x, y0 + h - 1, "boss_aimed",
                                big=self.muzzle > 0.06)
