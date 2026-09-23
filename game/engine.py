"""Core game orchestration: states, loop updates, collisions, spawning.

The Game class owns every entity list and system. main.py only calls
run() which pumps input -> update -> render at TARGET_FPS with
delta-time. All gameplay tuning lives in game/config.py.
"""

import json
import math
import random
import time
from pathlib import Path

from entities.boss import Boss
from entities.enemy import Enemy
from entities.player import Player
from entities.powerup import PowerUp
from entities.projectile import Projectile, player_shots
from game import config as CFG
from game.state import GameState, RunStats
from rendering import colors as C
from rendering import sprites as S
from rendering import aurora as A
from rendering import enemies_art as EA
from rendering.aurora import tc
from rendering.effects import Announcement, DamageFlash, ScreenShake, Starfield
from systems import collision as COL
from systems.audio import AudioSystem
from systems.input import (CONFIRM, DEBUG, DOWN, LEFT, MUTE, NOVA, PAUSE,
                           QUIT, RIGHT, SHOOT, UP)
from systems.particles import ParticleSystem
from systems.scoring import ScoreSystem
from systems.waves import WaveManager
from ui import hud as HUD
from ui import menu as MENU

SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "save.json"


def load_save():
    default = {"high_score": 0, "highest_wave": 0, "muted": False,
               "stats": {"kills": 0, "best_combo": 0, "time": 0, "victories": 0}}
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # validate shape; fall back gracefully on corruption
        out = dict(default)
        out.update({k: data.get(k, v) for k, v in default.items()})
        if not isinstance(out["stats"], dict):
            out["stats"] = default["stats"]
        return out
    except Exception:
        return dict(default)


def write_save(data):
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class Game:
    def __init__(self, renderer, input_sys):
        self.renderer = renderer
        self.input = input_sys
        self.save = load_save()
        self.audio = AudioSystem(muted=bool(self.save.get("muted", False)))
        self.particles = ParticleSystem()
        self.stars = Starfield()
        self.shake = ScreenShake()
        self.flash = DamageFlash()
        self.ann = Announcement()
        self.score = ScoreSystem()
        self.waves = WaveManager()
        self.stats = RunStats()
        self.state = GameState.MENU
        self.player = Player(60, 28)
        self.enemies = []
        self.pbullets = []
        self.ebullets = []
        self.powerups = []
        self.explosions = []  # {x,y,t,dur,big}
        self.boss = None
        self.menu_sel = 0
        self.menu_t = 0.0
        self.brief_t = 0.0
        self.state_t = 0.0
        self.over_t = 0.0
        self.new_best = False
        self.last_hit_by = "—"  # death-recap: what dealt the final blow
        self.tut_queue = []     # first-minute onboarding toasts
        self.tut_powerup_shown = False
        self.debug = False
        self.fps = 60.0
        self.frame_ms = 16.0
        self.logic_ms = 0.0   # update() cost (debug overlay)
        self.render_ms = 0.0  # render() cost (debug overlay)
        self.nova_anim = None  # {x,y,t}
        self.warp = False
        self.low_hp_warned = False

    # ------------------------------------------------------------ lifecycle
    def reset_run(self):
        w, h = self.renderer.width, self.renderer.height
        self.score = ScoreSystem()
        self.stats = RunStats()
        self.waves = WaveManager()
        self.enemies.clear()
        self.pbullets.clear()
        self.ebullets.clear()
        self.powerups.clear()
        self.explosions.clear()
        self.particles.clear()
        self.boss = None
        self.player = Player(w / 2, h - 6)
        self.player.novas = 1
        self.new_best = False
        self.nova_anim = None
        self.stars.init_stars(w, h, count=max(70, w * h // 38),
                              top_reserved=CFG.HUD_HEIGHT + 1)
        self.waves.wave = 0
        self.waves.between_waves = True
        self.waves.intermission = 1.6
        self.ann.show("STARFALL PROTOCOL", "defend the Helios gate",
                      duration=2.0, color=C.BRIGHT_CYAN)
        # first-minute onboarding: learn by playing, one idea at a time
        self.tut_queue = [
            (2.6, "MOVE: WASD / ARROWS — HOLD SPACE TO FIRE", C.HUD_TEXT),
            (12.0, "DODGE THE RED — CHAIN KILLS FOR COMBO", C.HUD_TEXT),
        ]
        self.tut_powerup_shown = False
        self.last_hit_by = "—"

    def bounds(self):
        r = self.renderer
        return (2, r.width - 3, CFG.HUD_HEIGHT + 2, r.height - 4)

    # ---------------------------------------------------------------- update
    def update(self, dt, inp):
        self.state_t += dt
        self.menu_t += dt
        # global keys
        if inp.was_pressed(MUTE):
            muted = self.audio.toggle()
            self.save["muted"] = muted
            write_save(self.save)
        if inp.was_pressed(DEBUG):
            self.debug = not self.debug

        if self.state == GameState.MENU:
            self._update_menu(dt, inp)
        elif self.state == GameState.CONTROLS:
            if inp.was_pressed(CONFIRM) or inp.was_pressed(QUIT):
                self.audio.play("menu")
                self.state = GameState.MENU
                self.state_t = 0
        elif self.state == GameState.SCORES:
            if inp.was_pressed(CONFIRM) or inp.was_pressed(QUIT):
                self.audio.play("menu")
                self.state = GameState.MENU
                self.state_t = 0
        elif self.state == GameState.BRIEFING:
            self.brief_t += dt
            if self.brief_t > 3.4 or inp.was_pressed(CONFIRM):
                self.state = GameState.PLAYING
                self.state_t = 0
                self.audio.play("wave")
        elif self.state == GameState.PLAYING:
            self._update_playing(dt, inp)
        elif self.state == GameState.PAUSED:
            if inp.was_pressed(PAUSE) or inp.was_pressed(CONFIRM):
                self.state = GameState.PLAYING
                self.audio.play("menu")
            elif inp.was_pressed(QUIT):
                self._to_menu()
        elif self.state == GameState.GAME_OVER:
            self.over_t += dt
            self.particles.update(dt)
            self._update_explosions(dt)
            self.score.update(dt)
            if self.over_t > 0.8:
                if inp.was_pressed(CONFIRM):
                    self.reset_run()
                    self.state = GameState.BRIEFING
                    self.brief_t = 0
                    self.state_t = 0
                elif inp.was_pressed(QUIT):
                    self._to_menu()
        elif self.state == GameState.VICTORY:
            self.over_t += dt
            self.particles.update(dt)
            self._update_explosions(dt)
            self.score.update(dt)
            if inp.was_pressed(CONFIRM):
                # continue endless
                self.state = GameState.PLAYING
                self.state_t = 0
                self.ann.show("ENDLESS MODE", "hold the line, pilot",
                              color=C.BRIGHT_MAGENTA)
            elif inp.was_pressed(QUIT):
                self._to_menu()

        # ambient systems always tick lightly
        self.shake.update(dt)
        self.flash.update(dt)
        self.ann.update(dt)

    def _to_menu(self):
        self.state = GameState.MENU
        self.state_t = 0
        self.menu_sel = 0

    def _update_menu(self, dt, inp):
        if inp.was_pressed(UP):
            self.menu_sel = (self.menu_sel - 1) % len(MENU.MENU_ITEMS)
            self.audio.play("menu")
        if inp.was_pressed(DOWN):
            self.menu_sel = (self.menu_sel + 1) % len(MENU.MENU_ITEMS)
            self.audio.play("menu")
        if inp.was_pressed(QUIT):
            # ESC on menu = exit handled by main loop
            self.want_exit = True
        if inp.was_pressed(CONFIRM):
            self.audio.play("menu")
            pick = MENU.MENU_ITEMS[self.menu_sel]
            if pick == "START GAME":
                self.reset_run()
                self.state = GameState.BRIEFING
                self.brief_t = 0
                self.state_t = 0
            elif pick == "CONTROLS":
                self.state = GameState.CONTROLS
                self.state_t = 0
            elif pick == "HIGH SCORES":
                self.state = GameState.SCORES
                self.state_t = 0
            elif pick == "EXIT":
                self.want_exit = True

    # --------------------------------------------------------------- playing
    def _update_playing(self, dt, inp):
        r = self.renderer
        min_x, max_x, min_y, max_y = self.bounds()
        p = self.player
        self.stats.time_alive += dt
        # onboarding toasts: one idea at a time, never clobber warnings
        if (self.tut_queue and not self.ann.active
                and self.stats.time_alive >= self.tut_queue[0][0]):
            _, text, col = self.tut_queue.pop(0)
            self.ann.show(text, "", duration=2.4, color=col)

        if inp.was_pressed(QUIT):
            self._to_menu()
            return
        if inp.was_pressed(PAUSE):
            self.state = GameState.PAUSED
            self.state_t = 0
            return

        # --- movement input
        mx = (1 if inp.is_held(RIGHT) else 0) - (1 if inp.is_held(LEFT) else 0)
        my = (1 if inp.is_held(DOWN) else 0) - (1 if inp.is_held(UP) else 0)
        if mx and my:  # normalize diagonal
            mx *= 0.7071
            my *= 0.7071
        p.update(dt, mx, my, (min_x, max_x, min_y, max_y))

        # triple-engine exhaust from the Aurora's 3 nozzles (thrust-scaled)
        if p.alive:
            A.exhaust_particles(self.particles, p.x, p.y, p.thrust)

        # --- firing
        if p.alive and inp.is_held(SHOOT) and p.can_fire():
            p.on_fired()
            self.stats.shots += 1
            for b in player_shots(p.x, p.y, p.weapon_level,
                                  damage_mult=p.damage_mult()):
                self.pbullets.append(b)
            self.audio.play("laser")
            # muzzle energy particles at the Aurora's guns
            A.muzzle_particles(self.particles, p.x, p.y)

        # --- nova
        if inp.was_pressed(NOVA):
            self.fire_nova()

        # --- waves / spawning
        events = self.waves.update(dt, len(self.enemies), self.boss is not None)
        for ev in events:
            if ev == "__wave_started__":
                self._on_wave_started()
            elif ev == "__wave_cleared__":
                self._on_wave_cleared()
            else:
                self._spawn_enemy(ev)

        # --- entities
        self._update_enemies(dt)
        self._update_boss(dt)
        self._update_bullets(dt)
        self._update_powerups(dt)
        self._update_explosions(dt)
        self.particles.update(dt)
        self.score.update(dt)
        self.stars.update(dt, top_reserved=CFG.HUD_HEIGHT + 1,
                           speed_mult=1.0 + min(1.5, self.waves.wave * 0.06),
                           warp=self.nova_anim is not None)
        if self.nova_anim is not None:
            self.nova_anim["t"] += dt
            if self.nova_anim["t"] > 0.7:
                self.nova_anim = None

        # player death drift
        if not p.alive:
            p.dead_timer -= dt
            if p.dead_timer <= 0:
                if p.lives > 0:
                    p.lives -= 1
                    if p.lives <= 0:
                        self._game_over()
                    else:
                        p.respawn(r.width / 2, r.height - 6)
                        self.ann.show("SHIP RESTORED", f"{p.lives} lives left",
                                      color=C.SHIELD)
                else:
                    self._game_over()

        # low-hp audio warning (once per threshold crossing)
        if p.alive and p.hp / p.max_hp < 0.3 and not self.low_hp_warned:
            self.audio.play("warning")
            self.low_hp_warned = True
        if p.hp / p.max_hp > 0.45:
            self.low_hp_warned = False

        # persist best wave live
        if self.waves.wave > self.save.get("highest_wave", 0):
            self.save["highest_wave"] = self.waves.wave
            write_save(self.save)

    # ---------------------------------------------------------------- events
    def _on_wave_started(self):
        n = self.waves.wave
        self.audio.play("wave")
        if self.waves.is_boss_wave(n):
            final = (n >= CFG.WIN_WAVE)
            name = "OBLIVION PRIME" if final else "DREADNOUGHT"
            self.ann.show("!! WARNING !!", f"{name}ᴴ approaching",
                          duration=3.0, color=C.WARNING)
            self.audio.play("warning")
            w = self.renderer.width
            self.boss = Boss(w / 2, CFG.HUD_HEIGHT + 1, wave=n, final=final)
            self.shake.add(0.35)
        else:
            form = self.waves.formation.upper()
            self.ann.show(f"WAVE {n:02d}", f"{form} formation",
                          duration=2.0, color=C.BRIGHT_CYAN)
            # progressive tips on early waves (anticipation, not overload)
            now = self.stats.time_alive
            if n == 2:
                self.tut_queue.append((now + 1.0, "INTERCEPTORS HUNT YOU — KEEP MOVING",
                                       C.WARNING))
            elif n == 3:
                self.tut_queue.append((now + 1.0, "X — NOVA CANNON WHEN SWARMED",
                                       C.NOVA))
            # wave-start bonus nova every 3 waves
            if n % 3 == 0 and self.player.novas < CFG.NOVA_MAX:
                self.player.novas += 1

    def _on_wave_cleared(self):
        bonus = 250 * self.waves.wave
        self.score.add_bonus(bonus, self.renderer.width / 2,
                             self.renderer.height / 2, "WAVE BONUS")
        self.player.heal(12)
        self.player.add_shield(10)
        self.ann.show("SECTOR CLEAR", f"+{bonus} bonus · hull patched",
                      duration=1.8, color=C.OK)
        self.audio.play("powerup")

    def _spawn_enemy(self, kind):
        w = self.renderer.width
        n = 1
        x = self.waves.spawn_x(w, random.randint(0, 5), 6)
        y = CFG.HUD_HEIGHT + 1
        self.enemies.append(Enemy(kind, x, y, wave=max(1, self.waves.wave)))

    # -------------------------------------------------------- entity updates
    def _update_enemies(self, dt):
        p = self.player
        min_x, max_x, min_y, max_y = self.bounds()
        w = self.renderer.width
        for e in self.enemies:
            e.update(dt, p.x, p.y, self.pbullets)
            e.x = max(1, min(w - 2, e.x))
            # enemy fire (only if on screen and roughly above player)
            if e.want_fire() and e.y > min_y - 2 and e.y < p.y and p.alive:
                self._enemy_fire(e)
        # cull off-screen
        self.enemies = [e for e in self.enemies if e.y < max_y + 6 and not e.dead]

    def _enemy_fire(self, e):
        """Per-class attack visuals: color + pattern match the reference."""
        p = self.player
        dx, dy = p.x - e.x, p.y - e.y
        d = math.hypot(dx, dy) or 1.0
        sp = e.bullet_speed
        e.muzzle = 0.12

        def style(kind):
            ch, rgb, fb, radius = EA.PROJECTILE[kind]
            return ch, tc(rgb, fb), radius

        if e.kind == "tank":  # 3-way heavy spread, large orange shells
            ch, col, rad = style("tank")
            for ang in (-0.25, 0, 0.25):
                vx = (dx / d) * sp + ang * sp
                self.ebullets.append(Projectile(e.x, e.y + 3, vx, (dy / d) * sp,
                                                False, e.bullet_dmg, ch, col,
                                                radius=rad, source="TANK"))
        elif e.kind == "bomber":  # heavy slow bomb orb
            ch, col, rad = style("bomber")
            self.ebullets.append(Projectile(e.x, e.y + 3, dx / d * sp * 0.8,
                                            abs(dy / d) * sp + 6, False,
                                            e.bullet_dmg, ch, col, radius=rad,
                                            source="BOMBER ORB"))
        elif e.kind == "elite":  # green 3-spread from wing guns
            ch, col, rad = style("elite")
            lead = 0.35
            tx = p.x + p.vx * lead
            dx2 = tx - e.x
            d2 = math.hypot(dx2, dy) or 1.0
            for off in (-3, 0, 3):
                self.ebullets.append(Projectile(e.x + off, e.y + 3,
                                                dx2 / d2 * sp + off * 1.5,
                                                dy / d2 * sp, False,
                                                e.bullet_dmg, ch, col,
                                                radius=rad, source="ELITE"))
        elif e.kind == "interceptor":  # blue DUAL parallel bolts
            ch, col, rad = style("interceptor")
            for off in (-1.4, 1.4):
                self.ebullets.append(Projectile(
                    e.x + off, e.y + 3, dx / d * sp * 0.3 + off,
                    abs(dy / d) * sp, False, e.bullet_dmg, ch, col,
                    radius=rad, source="INTERCEPTOR"))
        else:  # fighter / minion: single red-orange dart
            ch, col, rad = style(e.kind if e.kind in EA.PROJECTILE else "fighter")
            self.ebullets.append(Projectile(e.x, e.y + 3, dx / d * sp * 0.4,
                                            abs(dy / d) * sp, False,
                                            e.bullet_dmg, ch, col, radius=rad,
                                            source=e.kind.upper()))

    def _update_boss(self, dt):
        if self.boss is None:
            return
        p = self.player
        w = self.renderer.width
        event = self.boss.update(dt, p.x, w)
        if event == "charge":
            self.ann.show("!! DREADNOUGHT CHARGE !!", "", duration=0.9,
                          color=C.WARNING)
            self.audio.play("warning")
        # phase-change FX: magenta shield-burst ring + announcement
        if self.boss.phase != self.boss.last_phase:
            self.boss.last_phase = self.boss.phase
            self.shake.add(0.3)
            self.audio.play("warning")
            for _ in range(26):
                import math as _m2
                ang = random.uniform(0, 6.2832)
                self.particles.spawn(
                    self.boss.x, self.boss.y,
                    vx=_m2.cos(ang) * 26, vy=_m2.sin(ang) * 14,
                    life=random.uniform(0.4, 0.8),
                    char=random.choice(["*", "o", "+"]),
                    color=tc((255, 90, 230), C.BRIGHT_MAGENTA))
            if self.boss.phase == 3:
                self.ann.show("!! DREADNOUGHT ENRAGED !!", "core overdrive",
                              duration=1.6, color=C.WARNING)
            elif self.boss.phase == 2:
                self.ann.show("BOSS PHASE 2", "radial fire + minions",
                              duration=1.6, color=C.ENEMY_ELITE)
        # boss attacks
        if self.boss.want_aimed() and p.alive:
            dx, dy = p.x - self.boss.x, p.y - self.boss.y
            d = math.hypot(dx, dy) or 1.0
            sp = 26.0
            n = 1 + self.boss.phase
            self.boss.muzzle = 0.15
            ch, rgb, fb, rad = EA.PROJECTILE["boss_aimed"]
            col = tc(rgb, fb)
            for i in range(n):
                off = (i - (n - 1) / 2) * 5.0
                self.ebullets.append(Projectile(
                    self.boss.x + off, self.boss.y + 6,
                    dx / d * sp + off * 0.6, abs(dy / d) * sp,
                    False, 12.0, ch, col, radius=rad, source="BOSS LASER"))
            self.audio.play("laser2")
        if self.boss.want_ring():
            import math as _m
            n = 14 + self.boss.phase * 6
            self.boss.muzzle = 0.2
            ch, rgb, fb, rad = EA.PROJECTILE["boss_ring"]
            col = tc(rgb, fb)
            for i in range(n):
                ang = (i / n) * 2 * _m.pi + self.boss.t
                self.ebullets.append(Projectile(
                    self.boss.x, self.boss.y + 2,
                    _m.cos(ang) * 20, abs(_m.sin(ang)) * 20 + 4,
                    False, 10.0, ch, col, radius=rad, source="BOSS RING"))
            self.audio.play("nova")
        if self.boss.want_minion():
            for _ in range(2 + self.boss.phase):
                self.enemies.append(Enemy("minion",
                                          self.boss.x + random.uniform(-10, 10),
                                          self.boss.y + 4,
                                          wave=self.waves.wave))
            self.ann.show("MINIONS DEPLOYED", "", duration=1.0,
                          color=C.ENEMY_ELITE)

    def _update_bullets(self, dt):
        min_x, max_x, min_y, max_y = self.bounds()
        p = self.player
        # move + cull
        alive_p, alive_e = [], []
        for b in self.pbullets:
            if b.update(dt) and 1 < b.y < max_y + 4 and 0 < b.x < self.renderer.width:
                alive_p.append(b)
                # trail sparkle for high weapon levels
                if p.weapon_level >= 4 and random.random() < 0.25:
                    self.particles.trail(b.x, b.y + 1, C.BULLET_PLAYER)
        for b in self.ebullets:
            if b.update(dt) and min_y - 6 < b.y < max_y + 4 and -2 < b.x < self.renderer.width + 2:
                alive_e.append(b)
        self.pbullets, self.ebullets = alive_p, alive_e

        # player bullets vs enemies
        for b in list(self.pbullets):
            hit_any = False
            for e in self.enemies:
                if COL.point_in_enemy(b.x, b.y, e):
                    dead = e.hit(b.damage)
                    self.stats.hits += 1
                    self.particles.sparks(b.x, b.y, C.BULLET_PLAYER, count=4)
                    hit_any = True
                    if dead:
                        self._kill_enemy(e)
                    else:
                        e.y -= 0.35  # impact nudge: hits feel physical
                        self.audio.play("hit")
                    break
            if hit_any:
                if b in self.pbullets:
                    self.pbullets.remove(b)
                continue
            # vs boss
            if self.boss is not None and COL.point_in_boss(b.x, b.y, self.boss):
                self.stats.hits += 1
                dead = self.boss.hit(b.damage)
                self.particles.sparks(b.x, b.y, C.BRIGHT_YELLOW, count=5)
                if b in self.pbullets:
                    self.pbullets.remove(b)
                if dead:
                    self._kill_boss()

        # enemy bullets vs player (+ graze: near-miss bonus for flying close)
        # Hitbox r=1.5 matches the compact 7x5 hull (forgiving core, shmup-fair).
        if p.alive:
            for b in list(self.ebullets):
                if COL.collides(b.x, b.y, b.radius, p.x, p.y, 1.5):
                    self.ebullets.remove(b)
                    self.stats.damage_taken += b.damage
                    self.last_hit_by = b.source or "ENEMY FIRE"
                    died = p.take_damage(b.damage)
                    self.flash.trigger()
                    self.shake.add(0.3)
                    A.damage_sparks(self.particles, p.x, p.y)
                    self.score.float_text(p.x, p.y - 7, f"-{int(b.damage)} HULL",
                                          C.BRIGHT_RED)
                    self.audio.play("hurt")
                    if died:
                        self._player_explosion()
                    break
                if not b.grazed and COL.collides(b.x, b.y, b.radius + 0.5,
                                                 p.x, p.y, 2.4):
                    b.grazed = True
                    self.score.add_bonus(5, b.x, b.y - 1, "GRAZE")
            # ram: enemies vs player
            for e in list(self.enemies):
                if COL.collides(e.x, e.y, e.radius, p.x, p.y, 1.8):
                    self.stats.damage_taken += 25.0
                    self.last_hit_by = f"RAM: {e.kind.upper()}"
                    died = p.take_damage(25.0)
                    e.hit(9999)
                    self._kill_enemy(e, silent=True)
                    self.flash.trigger()
                    self.shake.add(0.45)
                    A.damage_sparks(self.particles, p.x, p.y)
                    self.score.float_text(p.x, p.y - 7, "-25 HULL",
                                          C.BRIGHT_RED)
                    self.audio.play("hurt")
                    if died:
                        self._player_explosion()
                    break
            # boss ram
            if self.boss is not None and COL.collides(
                    self.boss.x, self.boss.y, 9.0, p.x, p.y, 1.8):
                self.stats.damage_taken += 40.0
                self.last_hit_by = "BOSS RAM"
                died = p.take_damage(40.0)
                self.flash.trigger()
                self.shake.add(0.6)
                if died:
                    self._player_explosion()

    def _update_powerups(self, dt):
        p = self.player
        max_y = self.renderer.height - 3
        for u in self.powerups:
            u.update(dt, p.x, p.y)
        # collect
        for u in list(self.powerups):
            if u.y > max_y + 2:
                self.powerups.remove(u)
                continue
            if p.alive and COL.collides(u.x, u.y, 1.5, p.x, p.y, 2.6):
                self.powerups.remove(u)
                self._apply_powerup(u)
        # cap
        self.powerups = self.powerups[-12:]

    def _apply_powerup(self, u):
        p = self.player
        self.stats.powerups += 1
        self.particles.pickup_burst(u.x, u.y)
        self.audio.play("powerup")
        if u.kind == "health":
            p.heal(30)
            self.score.float_text(u.x, u.y - 1, "HULL +30", C.OK)
        elif u.kind == "shield":
            p.add_shield(30)
            self.score.float_text(u.x, u.y - 1, "SHIELD +30", C.SHIELD)
        elif u.kind == "energy":
            p.energy = min(p.max_energy, p.energy + 40)
            if p.novas < CFG.NOVA_MAX:
                p.novas += 1
            self.score.float_text(u.x, u.y - 1, "ENERGY + NOVA", C.NOVA)
        elif u.kind == "rapid":
            p.rapid_timer = 12.0
            self.score.float_text(u.x, u.y - 1, "RAPID FIRE!", C.BRIGHT_YELLOW)
        elif u.kind == "double":
            p.double_timer = 15.0
            self.score.float_text(u.x, u.y - 1, "DOUBLE DMG!", C.BRIGHT_MAGENTA)
        elif u.kind == "bomb":
            if p.novas < CFG.NOVA_MAX:
                p.novas += 1
            self.score.float_text(u.x, u.y - 1, "NOVA +1", C.NOVA)
        elif u.kind == "weapon":
            p.weapon_level = min(5, p.weapon_level + 1)
            self.score.float_text(u.x, u.y - 1,
                                  f"WEAPON Lv.{p.weapon_level}", C.BRIGHT_WHITE)
        elif u.kind == "life":
            p.lives += 1
            self.score.float_text(u.x, u.y - 1, "EXTRA LIFE!", C.BRIGHT_GREEN)
        self.score.add_bonus(50, u.x, u.y, "SALVAGE")

    def _update_explosions(self, dt):
        alive = []
        for ex in self.explosions:
            ex["t"] += dt
            if ex["t"] < ex["dur"]:
                alive.append(ex)
        self.explosions = alive[-24:]

    # ---------------------------------------------------------------- combat
    def add_explosion(self, x, y, big=False, kind=None):
        self.explosions.append({"x": x, "y": y, "t": 0.0,
                                "dur": 0.9 if big else 0.55, "big": big,
                                "kind": kind})
        if kind in EA.WRECK_TINT:
            EA.wreck_particles(self.particles, x, y, kind)
        else:
            self.particles.explosion(x, y, count=40 if big else 22,
                                     power=34 if big else 24)
        self.audio.play("big_explosion" if big else "explosion")

    def _kill_enemy(self, e, silent=False):
        if e in self.enemies:
            self.enemies.remove(e)
        self.add_explosion(e.x, e.y, big=(e.kind in ("tank", "elite")),
                           kind=e.kind if e.kind in EA.WRECK_TINT else None)
        self.shake.add(0.22 if e.kind != "fighter" else 0.12)
        self.stats.kills += 1
        gained = self.score.add_kill(e.score, e.x, e.y)
        # POINT BLANK: close-range kills pay +50% (risk/reward)
        import math as _m
        if self.player.alive and _m.hypot(e.x - self.player.x,
                                          e.y - self.player.y) < 12:
            extra = max(5, int(e.score * 0.5))
            self.score.score += extra
            self.score.float_text(e.x, e.y - 3, f"POINT BLANK +{extra}",
                                  C.BRIGHT_YELLOW)
        # named takedowns for dangerous classes (positive reinforcement)
        if e.kind == "elite":
            self.score.add_bonus(100, e.x, e.y - 4, "ELITE DESTROYED")
        elif e.kind == "tank":
            self.score.add_bonus(50, e.x, e.y - 4, "TANK DOWN")
        # salvage drops; pity rule: hurt pilots see more drops (fairness)
        chance = 0.12 if e.kind not in ("tank", "elite") else 0.30
        if self.player.hp / self.player.max_hp < 0.3:
            chance += 0.15
        if random.random() < chance and len(self.powerups) < 6:
            kind = "life" if (random.random() < 0.03) else None
            self.powerups.append(PowerUp(e.x, e.y, kind=kind))
            if not self.tut_powerup_shown:
                self.tut_powerup_shown = True
                self.ann.show("SALVAGE THE DROP", "fly over [?] to collect",
                              duration=2.0, color=C.OK)
        if not silent:
            pass
        return gained

    def _kill_boss(self):
        b = self.boss
        if b is None:
            return
        self.boss = None
        self.add_explosion(b.x, b.y, big=True, kind="boss")
        self.add_explosion(b.x - 6, b.y - 2, big=False)
        self.add_explosion(b.x + 6, b.y + 2, big=False)
        self.shake.add(1.0)
        self.stats.kills += 1
        self.score.add_kill(b.score, b.x, b.y)
        # shower of salvage
        for _ in range(3):
            self.powerups.append(PowerUp(b.x + random.uniform(-8, 8), b.y))
        self.ebullets.clear()  # mercy: clear bullet hell on kill
        if self.waves.wave >= CFG.WIN_WAVE:
            self._victory()
        else:
            self.ann.show("DREADNOUGHT DESTROYED", f"+{b.score} pts",
                          duration=2.4, color=C.BRIGHT_YELLOW)
            self.audio.play("victory")

    def _player_explosion(self):
        p = self.player
        self.add_explosion(p.x, p.y, big=True)
        self.shake.add(0.8)
        # weapon downgrade on death (arcade forgiveness keeps Lv>=1)
        p.weapon_level = max(1, p.weapon_level - 1)

    def fire_nova(self):
        p = self.player
        if self.state != GameState.PLAYING or not p.alive:
            return
        if p.novas <= 0:
            self.score.float_text(p.x, p.y - 4, "NOVA EMPTY", C.BRIGHT_BLACK)
            self.audio.play("hit")
            return
        p.novas -= 1
        self.stats.novas += 1
        self.nova_anim = {"x": p.x, "y": p.y, "t": 0.0}
        self.audio.play("nova")
        self.shake.add(0.7)
        self.particles.nova_ring(p.x, p.y, 6, C.NOVA)
        # damage everything + wipe enemy bullets (bullet-clear bonus)
        cleared = len(self.ebullets)
        for b in self.ebullets:
            self.particles.sparks(b.x, b.y, C.NOVA, count=2)
        self.ebullets.clear()
        self.score.add_bonus(cleared * 5, p.x, p.y - 5, "CLEARED")
        R = CFG.NOVA_RADIUS
        for e in list(self.enemies):
            d = math.hypot((e.x - p.x) * 0.55, (e.y - p.y))
            if d < R:
                if e.hit(CFG.NOVA_DAMAGE):
                    self._kill_enemy(e)
        if self.boss is not None:
            d = math.hypot((self.boss.x - p.x) * 0.55, (self.boss.y - p.y))
            if d < R + 10:
                if self.boss.hit(CFG.NOVA_DAMAGE):
                    self._kill_boss()

    def _session_snapshot(self, result):
        return {
            "result": result,
            "wave": max(1, self.waves.wave),
            "duration": round(self.stats.time_alive, 1),
            "kills": self.stats.kills,
            "accuracy": round(self.stats.accuracy(), 1),
            "max_combo": self.score.best_combo,
            "powerups": self.stats.powerups,
            "damage_taken": round(self.stats.damage_taken, 1),
            "novas": self.stats.novas,
            "boss_phase": self.boss.phase if self.boss is not None else 0,
            "death_blow": self.last_hit_by,
            "score": self.score.score,
        }

    def _game_over(self):
        self.state = GameState.GAME_OVER
        self.over_t = 0.0
        self.state_t = 0
        self.audio.play("gameover")
        from systems import telemetry as TEL
        TEL.record(self._session_snapshot("loss"))
        sc = self.score.score
        if sc > self.save.get("high_score", 0):
            self.save["high_score"] = sc
            self.new_best = True
        st = self.save.setdefault("stats", {})
        st["kills"] = st.get("kills", 0) + self.stats.kills
        st["best_combo"] = max(st.get("best_combo", 0), self.score.best_combo)
        st["time"] = st.get("time", 0) + self.stats.time_alive
        write_save(self.save)

    def _victory(self):
        self.state = GameState.VICTORY
        self.over_t = 0.0
        self.audio.play("victory")
        from systems import telemetry as TEL
        TEL.record(self._session_snapshot("win"))
        if self.score.score > self.save.get("high_score", 0):
            self.save["high_score"] = self.score.score
            self.new_best = True
        st = self.save.setdefault("stats", {})
        st["victories"] = st.get("victories", 0) + 1
        st["kills"] = st.get("kills", 0) + self.stats.kills
        st["best_combo"] = max(st.get("best_combo", 0), self.score.best_combo)
        st["time"] = st.get("time", 0) + self.stats.time_alive
        write_save(self.save)
        self.ann.show("VICTORY", "", duration=2.0, color=C.BRIGHT_YELLOW)

    # ---------------------------------------------------------------- render
    def render(self):
        r = self.renderer
        w, h = r.width, r.height
        if w < CFG.MIN_W or h < CFG.MIN_H:
            r.clear_buffers()
            r.text_centered(h // 2 - 1, "TERMINAL TOO SMALL", C.WARNING + C.BOLD)
            r.text_centered(h // 2 + 1,
                            f"need {CFG.MIN_W}x{CFG.MIN_H}, got {w}x{h} — resize to play",
                            C.HUD_TEXT)
            shx, shy = self.shake.offset()
            r.present(shx, shy)
            return

        if self.state == GameState.MENU:
            MENU.draw_menu(r, self.menu_sel,
                           high_score=self.save.get("high_score", 0),
                           wave_best=self.save.get("highest_wave", 0),
                           t=self.menu_t)
            r.present(0, 0)
            return
        if self.state == GameState.CONTROLS:
            r.clear_buffers()
            MENU.draw_controls(r)
            r.present(0, 0)
            return
        if self.state == GameState.SCORES:
            r.clear_buffers()
            MENU.draw_scores(r, self.save)
            r.present(0, 0)
            return
        if self.state == GameState.BRIEFING:
            r.clear_buffers()
            MENU.draw_briefing(r, self.brief_t)
            r.present(0, 0)
            return

        # ---- world states (playing / paused / over / victory share field)
        r.clear_buffers()
        narrow = w < 100
        self.stars.draw(r)
        for u in self.powerups:
            u.draw(r)
        for e in self.enemies:
            e.draw(r)
        if self.boss is not None:
            self.boss.draw(r)
        for b in self.ebullets:
            b.draw(r)
        for b in self.pbullets:
            b.draw(r)
        # explosions: per-class tinted wrecks, else generic starburst
        for ex in self.explosions:
            t = ex["t"] / ex["dur"]
            kind = ex.get("kind")
            if kind in EA.WRECK_TINT:
                stage = max(0, min(3, int(t * 4)))
                grid = EA.destroy_frame(kind, stage)
                w = len(grid[0])
                r.rich_sprite(ex["x"] - w / 2, ex["y"] - len(grid) / 2, grid)
                continue
            frame = S.explosion_frame(t)
            if frame:
                ww = max(len(row) for row in frame)
                col = C.BRIGHT_YELLOW if t < 0.5 else C.ENEMY
                r.sprite(ex["x"] - ww / 2, ex["y"] - len(frame) / 2, frame, col)
        self.particles.draw(r)
        self.player.draw(r, narrow=narrow)
        # nova expanding ring frame
        if self.nova_anim is not None:
            t = self.nova_anim["t"] / 0.7
            idx = min(2, int(t * 3))
            frame = S.NOVA_FRAMES[idx]
            ww = max(len(row) for row in frame)
            r.sprite(self.nova_anim["x"] - ww / 2, self.nova_anim["y"] - 3,
                     frame, C.NOVA + C.BOLD)
        self.score.draw(r)
        HUD.draw_hud(r, self.player, self.score, max(1, self.waves.wave),
                     enemies_left=len(self.enemies) + (1 if self.boss else 0),
                     fps=self.fps, debug=self.debug,
                     n_entities=len(self.enemies) + len(self.pbullets) + len(self.ebullets),
                     n_particles=len(self.particles), frame_ms=self.frame_ms,
                     logic_ms=self.logic_ms, render_ms=self.render_ms)
        if self.boss is not None:
            HUD.draw_boss_bar(r, self.boss)
        # center announcements above mid-field
        self.ann.draw(r, h // 2 - 6)
        if self.state == GameState.PAUSED:
            MENU.draw_pause(r)
        elif self.state == GameState.GAME_OVER:
            MENU.draw_game_over(r, self.score, max(1, self.waves.wave),
                                self.stats, self.last_hit_by,
                                self.new_best, self.over_t)
        elif self.state == GameState.VICTORY:
            MENU.draw_victory(r, self.score, self.over_t)
        HUD.draw_bottom(r, muted=self.audio.muted,
                        state_name=self.state.name if self.debug else "")
        # damage flash: red border pulse
        if self.flash.active:
            for x in range(w):
                r.put(x, CFG.HUD_HEIGHT + 1, "▀", C.BRIGHT_RED)
                r.put(x, h - 3, "▄", C.BRIGHT_RED)
        shx, shy = self.shake.offset()
        r.present(shx, shy)
