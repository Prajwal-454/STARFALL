"""Animated HUD: top status panel + boss bar + warnings.

Alignment rules (terminal UI theory):
  * ASCII-only in the HUD — emoji/double-width glyphs render as 1 cell in
    len() but 2 cells on screen (or boxes on legacy code pages), which
    breaks centering, bar endpoints and box borders.
  * All right-column text is clamped to the box width; narrow terminals
    (<100 cols) get a compact layout instead of overlapping columns.
"""

import time

from game import config as CFG
from rendering import colors as C
from rendering.renderer import clip_to_width, disp_width


def _bar(frac, width):
    frac = max(0.0, min(1.0, frac))
    n = int(round(width * frac))
    return "█" * n + "░" * (width - n)


def draw_hud(renderer, player, score, wave, enemies_left=0, fps=60.0,
             debug=False, n_entities=0, n_particles=0, frame_ms=0.0,
             logic_ms=0.0, render_ms=0.0):
    w = renderer.width
    narrow = w < 100
    # top border
    renderer.box(0, 0, w, CFG.HUD_HEIGHT, C.HUD_BORDER, "STARFALL: TERMINAL WAR")
    score_s = f"SCORE: {score.score:08d}"
    renderer.text(w - disp_width(score_s) - 2, 0, score_s, C.SCORE)
    # bars — shrink on narrow screens so columns never overlap
    if narrow:
        bw = max(12, min(20, w - 44))
    else:
        bw = max(18, min(30, w - 52))
    pulse = int(time.perf_counter() * 4) % 2 == 0
    hp_col = C.BRIGHT_RED if player.hp / player.max_hp < 0.3 and pulse else C.ENEMY
    sh_col = C.SHIELD
    en_col = C.BRIGHT_YELLOW
    renderer.text(2, 1, "HP    ", C.HUD_TEXT)
    renderer.text(9, 1, _bar(player.hp / player.max_hp, bw),
                  hp_col if player.hp > 0 else C.DIM)
    renderer.text(10 + bw, 1, f" {int(player.hp):3d}", C.HUD_TEXT)
    renderer.text(2, 2, "SHIELD", C.HUD_TEXT)
    renderer.text(9, 2, _bar(player.shield / player.max_shield, bw), sh_col)
    renderer.text(10 + bw, 2, f" {int(player.shield):3d}", C.HUD_TEXT)
    if not narrow:
        renderer.text(2, 3, "ENERGY", C.HUD_TEXT)
        renderer.text(9, 3, _bar(player.energy / player.max_energy, bw), en_col)
    # nova pips — ASCII so width is exact on every code page
    filled = "#" * max(0, player.novas)
    empty = "-" * max(0, CFG.NOVA_MAX - player.novas)
    nova_s = f"NOVA [{filled}{empty}]"
    nova_x = 10 + bw + 8
    if nova_x + disp_width(nova_s) < w - 2:
        renderer.text(nova_x, 1, nova_s, C.NOVA)
    # right column: wave / combo / lives / weapon (clamped, never overlaps)
    right_x = w - 26 if not narrow else w - 22
    right_x = max(nova_x + disp_width(nova_s) + 2, right_x)
    renderer.text(right_x, 1, f"WAVE {wave:02d}", C.BRIGHT_CYAN)
    combo_s = f"COMBO x{score.combo}" if score.combo >= 2 else "COMBO --"
    combo_col = C.BRIGHT_MAGENTA if score.combo >= 8 else C.HUD_TEXT
    renderer.text(right_x, 2, clip_to_width(combo_s, w - right_x - 2), combo_col)
    lives_s = f"LIVES x{player.lives}  WPN Lv.{player.weapon_level}"
    renderer.text(right_x, 3, clip_to_width(lives_s, w - right_x - 2),
                  C.HUD_TEXT)
    # status line inside box
    renderer.text(2, 4, clip_to_width(
        f"HOSTILES: {enemies_left:02d}   BEST x{score.best_combo}", w - 4),
        C.BRIGHT_BLACK)
    if narrow:
        ctrl = "WASD move - SPACE fire - X nova - P pause"
    else:
        ctrl = "WASD/Arrows move - SPACE fire - X nova - P pause - M mute"
    renderer.text(2, 5, clip_to_width(ctrl, w - 4), C.BRIGHT_BLACK)
    if debug:
        dbg = (f"FPS:{fps:4.1f} ENT:{n_entities} PRT:{n_particles} "
               f"UPD:{logic_ms:4.1f} RND:{render_ms:4.1f}ms W:{w} H:{renderer.height}")
        renderer.text(max(2, w - disp_width(dbg) - 2), 4,
                      clip_to_width(dbg, w - 4), C.BRIGHT_GREEN)
    # low hp warning strip
    if player.alive and player.hp / player.max_hp < 0.3 and pulse:
        warn = "!! HULL CRITICAL !!"
        renderer.text_centered(CFG.HUD_HEIGHT, warn, C.WARNING + C.BOLD)


def draw_boss_bar(renderer, boss):
    w = renderer.width
    h = renderer.height
    # bottom-anchored but clear of the help line: bar at h-3, label at h-4
    y = h - 3
    label = f"BOSS {boss.name} [PHASE {boss.phase}]"
    renderer.text_centered(y - 1, clip_to_width(label, w - 4), C.BOSS + C.BOLD)
    bw = min(max(20, w - 20), 60)
    x0 = (w - bw) // 2
    renderer.bar(x0, y, bw, boss.frac, "█", "░", C.BOSS, C.BRIGHT_BLACK)


def draw_bottom(renderer, muted=False, state_name=""):
    w = renderer.width
    y = renderer.height - 1
    left = f"{'[MUTED]' if muted else '[SOUND ON]'}  F1 debug"
    renderer.text(1, y, clip_to_width(left, w - 2), C.BRIGHT_BLACK)
    if state_name:
        renderer.text(w - disp_width(state_name) - 1, y,
                      clip_to_width(state_name, w - 4), C.BRIGHT_BLACK)
