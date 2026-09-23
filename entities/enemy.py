"""Enemy ships with deterministic patterns + controlled randomness.

Kinds: fighter, interceptor, tank, bomber, elite, minion.
Each enemy has: pos/vel, hp, fire timers, age `t`, pattern seed, score.
Movement is pattern-based (sine, dive, strafe, weave, home) so it reads as
intentional AI rather than random jitter. Elites actively dodge incoming
player bullets.
"""

import math
import random

from game import config as CFG
from rendering import colors as C
from rendering import enemies_art as EA

ENEMY_STATS = {
    "fighter": {"hp": 20.0, "speed": 12.0, "fire": 2.4, "bullet": 22.0, "dmg": 8.0, "r": 2.2},
    "interceptor": {"hp": 14.0, "speed": 24.0, "fire": 1.8, "bullet": 30.0, "dmg": 7.0, "r": 2.0},
    "tank": {"hp": 90.0, "speed": 6.0, "fire": 3.0, "bullet": 18.0, "dmg": 14.0, "r": 3.2},
    "bomber": {"hp": 45.0, "speed": 9.0, "fire": 2.8, "bullet": 26.0, "dmg": 18.0, "r": 3.0},
    "elite": {"hp": 70.0, "speed": 16.0, "fire": 1.4, "bullet": 28.0, "dmg": 10.0, "r": 2.6},
    "minion": {"hp": 10.0, "speed": 20.0, "fire": 2.6, "bullet": 24.0, "dmg": 6.0, "r": 1.6},
}


class Enemy:
    def __init__(self, kind, x, y, wave=1):
        st = ENEMY_STATS.get(kind, ENEMY_STATS["fighter"])
        mult = CFG.enemy_hp_mult(wave)
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = st["speed"]
        self.hp = st["hp"] * mult
        self.max_hp = self.hp
        self.speed = st["speed"] * CFG.enemy_speed_mult(wave)
        self.fire_interval = st["fire"] / CFG.difficulty_mult(wave) ** 0.5
        self.bullet_speed = st["bullet"]
        self.bullet_dmg = st["dmg"] * (1.0 + (wave - 1) * 0.06)
        self.radius = st["r"]
        self.score = CFG.SCORES.get(kind, 100)
        self.t = random.uniform(0, 10)
        self.seed = random.uniform(0, 6.28)
        self.fire_timer = random.uniform(0.6, self.fire_interval)
        self.alt = False
        self.anim = 0.0
        self.flash = 0.0
        self.muzzle = 0.0  # shooting-animation timer
        self.base_x = float(x)
        self.dive_state = 0
        self.strafe_dir = random.choice([-1, 1])

    # ------------------------------------------------------------- update
    def update(self, dt, player_x, player_y, player_bullets):
        self.t += dt
        self.anim += dt
        if self.anim > 0.28:
            self.anim = 0.0
            self.alt = not self.alt
        self.flash = max(0.0, self.flash - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.fire_timer -= dt
        k = self.kind
        if k == "fighter":
            self.vx = math.sin(self.t * 2.0 + self.seed) * 14.0
            self.vy = self.speed
        elif k == "interceptor":
            # hunts player x, dives fast
            dx = player_x - self.x
            self.vx = max(-30, min(30, dx * 2.2)) + math.sin(self.t * 5) * 4
            self.vy = self.speed * 1.4
        elif k == "tank":
            self.vx = math.sin(self.t * 0.8 + self.seed) * 6.0
            self.vy = self.speed * 0.7
        elif k == "bomber":
            # strafes near the top third, slowly descends
            if self.y < 14:
                self.vy = self.speed * 0.5
                self.vx = self.strafe_dir * 12.0
                if self.x < 6 or self.x > 114:
                    self.strafe_dir *= -1
            else:
                self.vx = math.sin(self.t * 1.5) * 8.0
                self.vy = self.speed * 0.6
        elif k == "elite":
            # Lissajous weave + dodge
            self.vx = math.sin(self.t * 2.4 + self.seed) * 20.0
            self.vy = self.speed * 0.55 + math.cos(self.t * 1.3) * 3.0
            # dodge: if a player bullet is just above and close in x, sidestep
            for b in player_bullets:
                if b.friendly and 0 < (self.y - b.y) < 9 and abs(b.x - self.x) < 3.5:
                    self.vx += 34.0 if b.x < self.x else -34.0
                    break
        elif k == "minion":
            dx = player_x - self.x
            self.vx = max(-26, min(26, dx * 1.6))
            self.vy = self.speed
        self.x += self.vx * dt
        self.y += self.vy * dt

    def want_fire(self):
        if self.fire_timer <= 0:
            self.fire_timer = self.fire_interval * random.uniform(0.8, 1.25)
            return True
        return False

    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 0.12
        return self.hp <= 0

    @property
    def dead(self):
        return self.hp <= 0

    # ---------------------------------------------------------------- draw
    def draw(self, renderer):
        # All seven fleet classes render through enemies_art (nose-down,
        # engine up, per-class colors). One pipeline, no legacy sprites.
        w, h = EA.dims(self.kind)
        x0 = self.x - w / 2
        y0 = self.y - h / 2
        phase = int(self.t * 4) % 2
        if self.flash > 0:
            variant = "dmg"
        elif self.muzzle > 0:
            variant = "shoot"
        elif self.kind in ("bomber", "tank") and 0 < self.fire_timer < 0.6:
            variant = "warn"  # telegraph: heavy shot incoming, move!
        elif self.vx < -8:
            variant = "left"
        elif self.vx > 8:
            variant = "right"
        else:
            variant = "idle"
        # engine flames trail ABOVE the nose-down hull
        EA.draw_flames_up(renderer, self.x, y0 - 1, int(self.t * 8), self.kind)
        renderer.rich_sprite(x0, y0, EA.body_frame(self.kind, variant, phase))
        # muzzle flash below the nose while firing
        if self.muzzle > 0:
            EA.draw_muzzle_down(renderer, self.x, y0 + h - 1, self.kind,
                                big=self.muzzle > 0.06)
        # heavy-ship hp bar below the nose (clear of the top flames)
        if self.kind in ("tank", "elite", "bomber") and self.hp < self.max_hp:
            frac = max(0.0, self.hp / self.max_hp)
            n = max(1, int(6 * frac))
            renderer.text(x0, y0 + h, "▓" * n, C.ENEMY)
