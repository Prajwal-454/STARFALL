# ✦ STARFALL: TERMINAL WAR

A modern arcade space shooter that runs **entirely inside your terminal** —
no GUI window, no browser, no game engine. Pure Python stdlib + ANSI.

## Requirements

- Python 3.10+ (tested 3.13)
- Windows CMD / PowerShell / Windows Terminal (also works on Linux/macOS)
- Terminal size **120×35 or larger** recommended (minimum 80×24)
- No `pip install` needed — zero dependencies

## Run

```bash
cd starfall-terminal-war
python main.py
# optional debug overlay (FPS / entities / particles):
python main.py --debug
```

If Windows shows boxes instead of `✦ █ ╔`, switch your terminal font to
*Cascadia Mono / Consolas* and run `chcp 65001` first. Windows Terminal
renders everything perfectly out of the box.

## Controls

| Key | Action |
|---|---|
| W A S D / Arrows | Move (diagonals supported) |
| SPACE (hold) | Fire cannons |
| X / B / TAB | NOVA CANNON (clears bullets, heavy AoE) |
| P | Pause |
| M | Mute sound |
| R | Confirm / fast retry on game-over |
| F1 or \` | Debug overlay (FPS, update/render ms) |
| ENTER | Confirm |
| ESC | Back / quit |

> SHIFT alone can't be detected in a terminal, so **X / B** is the NOVA key.

## Gameplay

- **11 waves** of Fighters, Interceptors, Tanks, Bombers, Elites with
  formation spawns (line, V, sides, swarm, snake), then the **DREADNOUGHT**
  boss — beat wave 11 for **VICTORY**, then continue in endless mode.
- Bosses have 3 phases (aimed bursts → radial rings + minions → enraged
  charges), a warning banner, and a boss HP bar.
- Combo scoring (chain kills within 3.5s), wave bonuses, salvage bonuses.
- Power-ups: `[+]` hull, `[S]` shield, `[E]` energy+nova, `[F]` rapid,
  `[D]` double damage, `[B]` nova +1, `[W]` weapon level, `[1UP]` life.
- 3-layer parallax starfield, particles (exhaust, explosions, sparks,
  nova rings), screen shake, damage flash, floating score text, animated
  menus / briefing / pause / game-over / victory.

## The ship: THE AURORA

The player flies **THE AURORA** (`rendering/aurora.py`) — a compact 7×5-cell
layered true-color sprite built procedurally (mirrored construction, so it
is perfectly symmetric): pointed nose, deep-blue canopy with shine sweep,
swept wings with cyan leading edges, twin engine pods with amber lights,
and **three short animated exhausts** (6-frame cycle, climb lengthens
slightly). Frames: 4 idle (canopy/edge/amber pulse),
bank left/right (shear tilt), muzzle flash + recoil dip, pulsing shield
bubble, 2 damage-flash, 4-stage breakup (flash → split → fireball →
embers). Guns: nose cannon + 2 wing guns; exhaust particles stream from
all three nozzles. Set `STARFALL_16COLOR=1` on legacy consoles without
24-bit color support.

## The enemy fleet

Six reference-sheet classes in `rendering/enemies_art.py`, same
procedural/mirrored construction as the Aurora (nose-down: engines on top,
guns at the nose): **Fighter** 9×7 red dart, blue engine · **Interceptor**
11×9 long blue/cyan hull, amber lights, dual bolts · **Tank** 13×8 purple
armor, huge magenta core, 3-spread orange shells · **Bomber** 13×8
white/orange, heavy bomb orbs · **Elite** 13×9 cyan/green, triple engines,
green 3-spread · **Boss** 31×12 magenta capital ship, giant core, 5
engines, aimed lasers + radial rings. Every class has idle/bank/shoot/
damage frames, engine-flame cycle, muzzle flash, 4-stage tinted wreck, and
matching projectile + explosion colors. The boss adds core-charge
telegraphs, phase-change shield bursts, and a red rage tint in phase 3.

## Project layout

```
main.py                  entry + fixed-timestep 60fps loop
game/config.py           tuning + difficulty curve
game/state.py            GameState enum + run stats
game/engine.py           Game: states, spawning, collisions, rendering
rendering/renderer.py    buffered ANSI renderer (single write/frame)
rendering/sprites.py     ASCII/Unicode ship art
rendering/colors.py      palette
rendering/effects.py     shake, flash, announcements, starfield
entities/                player, enemy AI, boss, projectile, powerup
systems/                 input (non-blocking), particles, collision,
                         waves, scoring, audio (winsound, optional)
ui/                      menu, hud, briefing/pause/end screens
data/save.json           high score, best wave, stats (auto-created)
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Flicker | Use Windows Terminal; don't run inside an IDE console |
| `TERMINAL TOO SMALL` | Resize to ≥80×24 (120×35 ideal), game adapts live |
| No sound | Sound is `winsound.Beep` on Windows only; game plays fine muted (M) |
| Keys lag | CMD key-repeat: hold keys, game polls every frame — no Enter needed |
| Broken cursor/colors after crash | Engine restores cursor + colors + alt-screen on exit, even on exception |
| Corrupt `data/save.json` | Delete it; game recreates defaults automatically |

## Scoring

Fighter 100 · Interceptor 250 · Bomber 400 · Tank 500 · Elite 1000 ·
Boss 10000 · combo multiplier +1×/0.5 per 4 chain · wave bonus 250×wave.

Close-range kills pay **POINT BLANK +50%**; near-misses pay **GRAZE +5**.
Combo multiplier is capped at x5.

## Game feel systems

- **First minute teaches by playing**: move/fire toast, dodge+combo toast,
  wave-2 interceptor warning, wave-3 nova tip, first-drop salvage hint.
- **Readable heavies**: Bombers/Tanks blink a warning before firing; the
  boss core glows before lasers and ring bursts.
- **Fair failure**: hits show `-N HULL` floaters, game-over reports kills,
  combo, accuracy, time, and the final blow (`FINAL BLOW: BOMBER ORB`).
- **Pity salvage**: drop rate rises when hull is under 30%.
- **Local telemetry** (`data/telemetry.json`, gameplay facts only):
  `python -m systems.telemetry` prints a balance report (avg wave, top
  death wave, accuracy, nova-use rate).
