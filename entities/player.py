"""PlayerShip — THE AURORA: physics, weapons, damage, nova cannon.

Reusable component as specified by the ship design:

    PlayerShip
    ├── position / velocity      (x, y, vx, vy — smooth, non-grid movement)
    ├── health / shield          (hp, shield + regen, lives)
    ├── animation_state/frame    (idle / bank / shoot / damage / destroy)
    ├── sprite                   (AURORA layered true-color body frames)
    ├── engine_animation         (6-frame triple-exhaust cycle + thrust)
    ├── movement_animation       (bank shear + thrust-scaled flames)
    ├── shooting_animation       (muzzle flash + recoil dip + particles)
    ├── damage_animation         (white/red flash + sparks + shake hook)
    └── destruction_animation    (4-stage breakup drawn while dead)

Rendering pipeline per frame:
    Game State -> Player Entity -> Aurora frames -> particles
    -> TerminalRenderer.rich_sprite -> buffered frame -> CMD/PowerShell.
"""

import time

from game import config as CFG
from rendering import aurora as A

# Body half-extents (cells) used to keep the compact 7x5 hull on screen.
HALF_W = A.BODY_W // 2      # 3
NOSE_UP = 2                 # rows above center
TAIL_DOWN = 2               # body rows below center (flames may overhang)


class Player:
    def __init__(self, x=60.0, y=28.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.max_hp = CFG.PLAYER_MAX_HP
        self.hp = CFG.PLAYER_MAX_HP
        self.max_shield = CFG.PLAYER_MAX_SHIELD
        self.shield = CFG.PLAYER_MAX_SHIELD
        self.max_energy = CFG.PLAYER_MAX_ENERGY
        self.energy = CFG.PLAYER_MAX_ENERGY
        self.lives = 3
        self.weapon_level = 1
        self.fire_timer = 0.0
        self.invuln = 0.0
        self.regen_delay = 0.0
        self.flash = 0.0  # damage flash timer
        self.tilt = 0.0
        self.alive = True
        self.rapid_timer = 0.0
        self.double_timer = 0.0
        self.novas = 1
        self.engine_anim = 0.0
        self.dead_timer = 0.0
        # --- Aurora animation state ---
        self.animation_state = "idle"   # idle | left | right | shoot | damage | destroy
        self.animation_frame = 0
        self.anim_t = 0.0
        self.thrust = 0                 # -1 descend / 0 cruise / +1 climb
        self.muzzle = 0.0               # muzzle-flash timer
        self.dead_total = 1.4

    def reset_position(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0

    # ------------------------------------------------------------- update
    def update(self, dt, move_x, move_y, bounds):
        min_x, max_x, min_y, max_y = bounds
        min_x += HALF_W
        max_x -= HALF_W
        if max_x < min_x:
            mid = (min_x + max_x) / 2
            min_x = max_x = mid
        min_y += NOSE_UP
        max_y -= TAIL_DOWN
        if max_y < min_y:
            mid = (min_y + max_y) / 2
            min_y = max_y = mid
        # acceleration toward desired velocity (smooth, not grid-locked)
        want_vx = move_x * CFG.PLAYER_SPEED
        want_vy = move_y * CFG.PLAYER_SPEED
        k = min(1.0, CFG.PLAYER_ACCEL * dt / max(1.0, CFG.PLAYER_SPEED))
        self.vx += (want_vx - self.vx) * min(1.0, k * 3.2)
        self.vy += (want_vy - self.vy) * min(1.0, k * 3.2)
        # friction when no input
        if move_x == 0:
            self.vx -= self.vx * min(1.0, CFG.PLAYER_FRICTION * dt)
        if move_y == 0:
            self.vy -= self.vy * min(1.0, CFG.PLAYER_FRICTION * dt)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = max(min_x, min(max_x, self.x))
        self.y = max(min_y, min(max_y, self.y))
        # tilt follows horizontal velocity -> bank animation state
        target_tilt = max(-1.0, min(1.0, self.vx / CFG.PLAYER_SPEED))
        self.tilt += (target_tilt - self.tilt) * min(1.0, 10 * dt)
        # thrust follows vertical input: climb = bigger flames
        if move_y < 0:
            self.thrust = 1
        elif move_y > 0:
            self.thrust = -1
        else:
            self.thrust = 0
        # animation clock (idle cycle ~4 phases, engine 6-frame cycle)
        self.anim_t += dt
        self.animation_frame = int(self.anim_t * 6) % 4
        if self.tilt < -0.25:
            self.animation_state = "left"
        elif self.tilt > 0.25:
            self.animation_state = "right"
        elif self.muzzle > 0:
            self.animation_state = "shoot"
        elif self.flash > 0:
            self.animation_state = "damage"
        else:
            self.animation_state = "idle"
        # timers
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.rapid_timer = max(0.0, self.rapid_timer - dt)
        self.double_timer = max(0.0, self.double_timer - dt)
        self.regen_delay = max(0.0, self.regen_delay - dt)
        self.engine_anim += dt
        # shield regen + energy trickle
        if self.regen_delay <= 0 and self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + CFG.SHIELD_REGEN_RATE * dt)
        self.energy = min(self.max_energy, self.energy + 6.0 * dt)

    def fire_cooldown(self):
        base = CFG.PLAYER_FIRE_COOLDOWN[min(4, max(0, self.weapon_level - 1))]
        if self.rapid_timer > 0:
            base *= 0.5
        return base

    def can_fire(self):
        return self.fire_timer <= 0 and self.alive

    def on_fired(self):
        self.fire_timer = self.fire_cooldown()
        self.muzzle = 0.12  # muzzle-flash + recoil window

    def damage_mult(self):
        return 2.0 if self.double_timer > 0 else 1.0

    # ------------------------------------------------------------- damage
    def take_damage(self, amount):
        if not self.alive or self.invuln > 0:
            return False
        remaining = amount
        if self.shield > 0:
            absorbed = min(self.shield, remaining)
            self.shield -= absorbed
            remaining -= absorbed
        self.hp -= remaining
        self.flash = 0.25
        self.invuln = 0.35
        self.regen_delay = CFG.SHIELD_REGEN_DELAY
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.dead_timer = self.dead_total
            self.animation_state = "destroy"
            return True
        return False

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def add_shield(self, amount):
        self.shield = min(self.max_shield, self.shield + amount)

    def respawn(self, x, y):
        self.reset_position(x, y)
        self.hp = self.max_hp
        self.shield = self.max_shield
        self.energy = self.max_energy
        self.alive = True
        self.invuln = CFG.INVULN_TIME
        self.vx = self.vy = 0.0
        self.animation_state = "idle"

    # ------------------------------------------------------------ helpers
    def nose_pos(self):
        dx, dy = A.NOSE
        return (self.x + dx, self.y + dy)

    def gun_pos(self, i=0):
        dx, dy = A.GUNS[i % len(A.GUNS)]
        return (self.x + dx, self.y + dy)

    # --------------------------------------------------------------- draw
    def draw(self, renderer, narrow=False):
        # --- destruction sequence plays at the wreck position while dead
        if not self.alive:
            if self.dead_timer > 0:
                prog = 1.0 - max(0.0, self.dead_timer) / max(0.01, self.dead_total)
                stage = max(0, min(3, int(prog * 4)))
                x0 = self.x - A.BODY_W / 2
                y0 = self.y - A.BODY_H / 2
                renderer.rich_sprite(x0, y0, A.destroy_frame(stage))
            return
        # invulnerability blink (classic arcade)
        if self.invuln > 0 and int(time.perf_counter() * 12) % 2 == 0:
            return
        # pick hull frame
        if self.flash > 0:
            kind, phase = "dmg", int(self.anim_t * 20) % 2
        elif self.tilt < -0.25:
            kind, phase = "left", self.animation_frame
        elif self.tilt > 0.25:
            kind, phase = "right", self.animation_frame
        else:
            kind, phase = "idle", self.animation_frame
        recoil = 1 if (self.muzzle > 0.07) else 0  # subtle recoil dip
        x0 = self.x - A.BODY_W / 2
        y0 = self.y - A.BODY_H / 2 + recoil
        # triple-engine flames first (ship overlaps their roots)
        eng_idx = int(self.engine_anim * 12) % 6
        A.draw_flames(renderer, self.x, y0 + A.BODY_H, eng_idx, self.thrust)
        # hull
        renderer.rich_sprite(x0, y0, A.body_frame(kind, phase))
        # muzzle flash on the guns while firing
        if self.muzzle > 0:
            nx, ny = self.nose_pos()
            A.draw_muzzle(renderer, self.x, self.y + recoil,
                          big=self.muzzle > 0.06)
        # transparent pulsing shield bubble (never hides the ship)
        if self.shield > 0:
            A.draw_shield(renderer, self.x, self.y + recoil, self.anim_t)
