"""Headless functional test for STARFALL (no terminal needed)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from game.engine import Game
from game.state import GameState
from rendering.renderer import TerminalRenderer
from systems import collision as COL
from systems.input import InputState
from entities.enemy import Enemy
from entities.powerup import PowerUp


class DummyRenderer(TerminalRenderer):
    def __init__(self):
        super().__init__()
        self.width, self.height = 120, 35
        self.refresh_size = lambda: (120, 35)
        self.chars = [[" "] * 120 for _ in range(35)]
        self.colors = [[""] * 120 for _ in range(35)]
    def present(self, *a, **k):
        pass
    def setup(self):
        pass
    def restore(self):
        pass


class FakeInput:
    def __init__(self):
        self.s = InputState()
    def set(self, held=(), pressed=()):
        self.s.held = set(held)
        self.s.pressed = set(pressed)
        return self.s
    def poll(self):
        return self.s


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    assert cond, name


r = DummyRenderer()
inp = FakeInput()
g = Game(r, inp)
g.want_exit = False
g.stars.init_stars(120, 35, count=40, top_reserved=8)

# 1. menu -> briefing -> playing
check("starts in MENU", g.state == GameState.MENU)
g.update(1/60, inp.set(pressed={"confirm"}))  # START GAME selected by default
check("confirm starts BRIEFING", g.state == GameState.BRIEFING)
g.update(3.5, inp.set())
check("briefing advances to PLAYING", g.state == GameState.PLAYING)

# 2. movement changes player pos
x0, y0 = g.player.x, g.player.y
for _ in range(30):
    g.update(1/60, inp.set(held={"right", "up"}))
check("player moves right/up", g.player.x > x0 and g.player.y < y0)

# 3. shooting spawns bullets
n0 = len(g.pbullets)
for _ in range(20):
    g.update(1/60, inp.set(held={"shoot"}))
check("shooting produces bullets", len(g.pbullets) > n0 or g.stats.shots > 0)

# 4. waves spawn enemies
spawned = False
for _ in range(60*8):
    g.update(1/60, inp.set())
    if g.enemies:
        spawned = True
        break
check("wave spawns enemies", spawned)

# 5. collision helper sanity
check("collides near", COL.collides(0, 0, 1, 0.5, 0.5, 1))
check("no collide far", not COL.collides(0, 0, 1, 50, 50, 1))

# 6. kill enemy -> score + combo + explosion
e = Enemy("fighter", g.player.x, g.player.y - 10, wave=1)
g.enemies.append(e)
s0 = g.score.score
# drop a bullet right on it
from entities.projectile import Projectile
g.pbullets.append(Projectile(e.x, e.y, 0, 0, True, 9999))
g.update(1/60, inp.set())
check("enemy kill scores", g.score.score > s0 and g.stats.kills >= 1)

# 7. powerup collect
u = PowerUp(g.player.x, g.player.y, kind="health")
g.player.hp = 10
g.powerups.append(u)
g.update(1/60, inp.set())
check("powerup heals", g.player.hp > 10)

# 8. nova clears + damages
g.player.novas = 2
g.enemies.append(Enemy("fighter", g.player.x + 2, g.player.y - 5, wave=1))
from systems.input import NOVA
g.update(1/60, inp.set(pressed={NOVA}))
check("nova consumed", g.player.novas == 1)

# 9. boss spawn on wave 5 path
g.waves.wave = 4
g.waves.between_waves = True
g.waves.intermission = 0.01
g.enemies.clear()
g.boss = None
wave_started = False
for _ in range(60*3):
    g.update(1/60, inp.set())
    if g.boss is not None:
        wave_started = True
        break
check("boss wave spawns boss", wave_started)
# kill boss -> victory if wave>=WIN? wave 5 boss kill should NOT victory
bid = g.boss
assert bid is not None
bid.hp = 1
g.pbullets.append(Projectile(bid.x, bid.y, 0, 0, True, 9999))
g.update(1/60, inp.set())
check("boss kill clears boss", g.boss is None)

# 10. game over path
g.player.lives = 1
g.player.hp = 5
g.player.shield = 0
g.player.invuln = 0
g.player.take_damage(999)
g.player.dead_timer = 0.01
for _ in range(10):
    g.update(1/60, inp.set())
check("death leads to GAME_OVER", g.state == GameState.GAME_OVER)

# 11. save file valid
import json
d = json.loads(open("starfall-terminal-war/data/save.json", encoding="utf-8").read())
check("save has high_score", "high_score" in d)

# 12. render all states without exception
for st in [GameState.MENU, GameState.CONTROLS, GameState.SCORES,
           GameState.BRIEFING, GameState.PLAYING, GameState.PAUSED,
           GameState.GAME_OVER, GameState.VICTORY]:
    g.state = st
    g.render()
check("all states render", True)

# 13. perf: 300 playing updates under budget
import time
g.state = GameState.PLAYING
g.reset_run()
g.state = GameState.PLAYING
t0 = time.perf_counter()
for _ in range(300):
    g.update(1/60, inp.set(held={"shoot", "right"}))
dt = time.perf_counter() - t0
print(f"300 updates in {dt*1000:.0f}ms ({dt/300*1000:.2f}ms/frame logic only)")
check("logic fast enough (<8ms avg)", dt/300 < 0.008)

print("\nALL HEADLESS TESTS PASSED")

# ------------------------------------------------------------- AURORA ship
from rendering import aurora as AUR

body = AUR.body_frame("idle", 0)
check("aurora body 7x5", len(body) == 5 and all(len(r) == 7 for r in body))
check("aurora 20+ cells", sum(1 for r in body for c in r if c) >= 20)
sym = True
for ph in range(4):
    b = AUR.body_frame("idle", ph)
    for y in range(AUR.BODY_H):
        if list(b[y]) != list(b[y][::-1]):
            sym = False
check("aurora idle symmetric", sym)
sym_d = True
for ph in range(2):
    b = AUR.body_frame("dmg", ph)
    for y in range(AUR.BODY_H):
        if list(b[y]) != list(b[y][::-1]):
            sym_d = False
check("aurora damage symmetric", sym_d)
check("aurora 4 idle phases differ",
      len({repr(AUR.body_frame("idle", ph)) for ph in range(4)}) > 1)
check("aurora bank frames", AUR.body_frame("left", 0) != AUR.body_frame("right", 0))
check("aurora 4 destroy stages",
      len({repr(AUR.destroy_frame(s)) for s in range(4)}) == 4)
check("aurora 6 flame lengths vary", len(set(AUR.flame_length(i) for i in range(6))) >= 4)
check("aurora thrust scales flames", AUR.flame_length(2, 1) > AUR.flame_length(2, -1))
check("aurora guns in hull", all(abs(dx) <= 5 and -4 <= dy <= 1 for dx, dy in AUR.GUNS))
check("aurora 3 exhausts", len(AUR.EXHAUST_X) == 3 and 0 in AUR.EXHAUST_X)
check("aurora frames cached", AUR.body_frame("idle", 0) is AUR.body_frame("idle", 0))
# draw every ship state headless (uses DummyRenderer.rich_sprite)
p2 = g.player
for kind, ph in [("idle", 0), ("left", 1), ("right", 2), ("dmg", 0)]:
    r.clear_buffers()
    r.rich_sprite(40, 15, AUR.body_frame(kind, ph))
AUR.draw_flames(r, 60, 25, 3, 0)
AUR.draw_muzzle(r, 60, 20, True)
AUR.draw_shield(r, 60, 20, 1.0)
r.rich_sprite(40, 15, AUR.destroy_frame(2))
p2.draw(r)
p2.alive = False
p2.dead_timer = 1.0
p2.draw(r)
p2.alive = True
check("aurora all draws run", True)

print("\nALL AURORA TESTS PASSED")

# ------------------------------------------------------------- ENEMY FLEET
from rendering import enemies_art as FEA
from entities.enemy import Enemy as EnemyEnt
from entities.boss import Boss as BossEnt

check("fleet 7 sizes sane",
      FEA.dims("minion")[0] < FEA.dims("fighter")[0] < FEA.dims("tank")[0]
      <= FEA.dims("boss")[0] and FEA.dims("boss") == (31, 12)
      and FEA.dims("minion") == (5, 3))
check("fleet distinct silhouettes",
      len({repr(FEA.body_frame(k, "idle", 0)) for k in FEA.SIZES}) == 7)
sym_f = True
for k in FEA.SIZES:
    for v, ph in [("idle", 0), ("idle", 1), ("dmg", 0), ("charge", 0), ("warn", 1)]:
        b = FEA.body_frame(k, v, ph, k == "boss")
        for y in range(len(b)):
            if list(b[y]) != list(b[y][::-1]):
                sym_f = False
                print("ASYMM", k, v, ph, y)
check("fleet all frames symmetric", sym_f)
check("fleet bank frames differ",
      FEA.body_frame("fighter", "left", 0) != FEA.body_frame("fighter", "right", 0))
check("fleet rage tint", FEA.body_frame("boss", "idle", 0, True) !=
      FEA.body_frame("boss", "idle", 0, False))
check("fleet wrecks 4 stages",
      all(len({repr(FEA.destroy_frame(k, s)) for s in range(4)}) == 4
          for k in ("fighter", "tank", "elite", "boss")))
check("fleet projectile identities",
      set(FEA.PROJECTILE) >= {"fighter", "interceptor", "tank", "bomber",
                              "elite", "minion", "boss_aimed", "boss_ring"})
check("fleet wreck tints", set(FEA.WRECK_TINT) >= set(FEA.SIZES) | {"minion"})
# draw every kind + boss phases headless
for k in list(FEA.SIZES) + ["minion"]:
    e = EnemyEnt(k if k != "boss" else "fighter", 60, 20, wave=3)
    e.kind = k
    e.vx = -12
    e.muzzle = 0.1
    e.flash = 0.1
    r.clear_buffers()
    if k == "boss":
        continue
    e.draw(r)
    e.vx = 12
    e.flash = 0
    e.draw(r)
br = BossEnt(60, 14, wave=5)
for st in [(1, 3.0, 0.0), (2, 0.5, 0.0), (3, 3.0, 0.2)]:
    br.phase, br.ring_timer, br.muzzle = st
    br.flash = 0.1
    r.clear_buffers()
    br.draw(r)
    br.flash = 0
    br.draw(r)
br.charging = 0.5
br.draw(r)
check("fleet all draws run", True)
# per-class fire patterns
import game.engine as ENG
for k, want_n in [("fighter", 1), ("interceptor", 2), ("tank", 3),
                  ("bomber", 1), ("elite", 3), ("minion", 1)]:
    e = EnemyEnt("fighter", 60, 15, wave=2)
    e.kind = k
    n0 = len(g.ebullets)
    g.player.x, g.player.y = 60, 28
    ENG.Game._enemy_fire(g, e)
    check(f"fleet {k} fires {want_n}", len(g.ebullets) - n0 == want_n)
    g.ebullets.clear()
# tinted wreck recorded on kill
e = EnemyEnt("elite", 60, 15, wave=1)
g.enemies.append(e)
g._kill_enemy(e)
check("fleet kill records tint", g.explosions and g.explosions[-1].get("kind") == "elite")
r.clear_buffers()
g.state = GameState.PLAYING
g.render()
check("fleet wreck renders", True)

print("\nALL FLEET TESTS PASSED")

# ------------------------------------------------------------- GAME FEEL
from systems.input import InputSystem as RealInput
check("R key confirms (fast retry)", RealInput()._map_char("r") == {"confirm"})

# graze: near miss pays +5 once
g.state = GameState.PLAYING
g.player.x, g.player.y = 60, 28
g.player.hp = 100
g.player.shield = 60
g.player.invuln = 0
s0 = g.score.score
grz = Projectile(60, 28 - 3.1, 0, 5, False, 5, ".", "", source="FIGHTER")
g.ebullets.append(grz)
g.update(1 / 60, inp.set())
check("graze awards +5", g.score.score - s0 == 5 and grz.grazed)
check("graze is once-only", (lambda: (g.update(1 / 60, inp.set()),
                                      g.score.score - s0 == 5))())

# hurt floater + death-blow source
g.ebullets.clear()
g.player.invuln = 0
g.player.shield = 0
g.player.hp = 100
g.ebullets.append(Projectile(60, 28, 0, 5, False, 11, "!", "", source="ELITE"))
nfl = len(g.score.floaters)
g.update(1 / 60, inp.set())
check("hurt shows damage floater", len(g.score.floaters) > nfl)
check("death-blow source tracked", g.last_hit_by == "ELITE")

# knockback nudge on non-lethal hit
e = EnemyEnt("tank", 60, 15, wave=1)
e.hp = e.max_hp = 500
y0 = e.y
g.enemies.append(e)
g.pbullets.append(Projectile(60, 15, 0, 0, True, 10))
g.update(1 / 60, inp.set())
check("hits nudge enemies", e.y < y0 and e in g.enemies)

# point blank: close kill pays 1.5x base
from systems.scoring import ScoreSystem as SS
g.score = SS()
e2 = EnemyEnt("fighter", 61, 27, wave=1)
g.enemies.append(e2)
base = e2.score
g.pbullets.append(Projectile(61, 27, 0, 0, True, 9999))
g.update(1 / 60, inp.set())
check("point blank bonus", g.score.score - 0 >= int(base * 1.5))

# combo multiplier hard-capped at x5
sc = SS()
sc.combo, sc.combo_timer = 39, 3.5
check("combo capped x5", sc.add_kill(100, 0, 0) == 500)
sc2 = SS()
sc2.combo, sc2.combo_timer = 19, 3.5
check("combo x20 -> 3.5x", sc2.add_kill(100, 0, 0) == 350)

# pity drops: hurt pilots see more salvage (seeded, deterministic)
import random as _rnd
def drop_count(hp, seed):
    _rnd.seed(seed)
    n = 0
    g.player.hp = hp
    for _ in range(200):
        g.powerups.clear()
        ee = EnemyEnt("fighter", 60, 15, wave=1)
        g.enemies.append(ee)
        before = len(g.powerups)
        g._kill_enemy(ee)
        n += len(g.powerups) - before
        g.score = SS()
    return n
check("pity drops help low HP", drop_count(20, 7) > drop_count(100, 7))
g.player.hp = 100

# tutorial toast fires in the first seconds
g.reset_run()
g.state = GameState.PLAYING
for _ in range(240):
    g.update(1 / 60, inp.set())
check("tutorial toast shows", g.ann.active and "SPACE" in g.ann.main)

# boss phase-2 banner
g.reset_run()
g.state = GameState.PLAYING
g.waves.wave = 5
g.waves.wave_active = True
g.waves.between_waves = False
from entities.boss import Boss as B2
g.boss = B2(60, 12, wave=5)
g.boss.entering = False
g.boss.last_phase = 1
g.boss.hp = g.boss.max_hp * 0.5
g.update(1 / 60, inp.set())
check("phase 2 banner", "PHASE 2" in g.ann.main)

# telemetry records + reports
from systems import telemetry as TEL
TEL.record({"result": "loss", "wave": 3, "kills": 10, "accuracy": 50.0,
            "max_combo": 4, "powerups": 1, "damage_taken": 30,
            "novas": 0, "boss_phase": 0, "death_blow": "FIGHTER",
            "score": 1000, "duration": 60.0})
rep = TEL.report()
check("telemetry report", rep.get("sessions", 0) >= 1 and "top_death_wave" in rep)

print("\nALL FEEL TESTS PASSED")
