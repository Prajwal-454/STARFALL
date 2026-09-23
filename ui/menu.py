"""Menus, briefing, game-over, victory, pause — all animated, all live-render."""

import time

from rendering import colors as C
from rendering.renderer import clip_to_width, disp_width

LOGO = [
    " ███████╗████████╗ █████╗ ██████╗ ███████╗ █████╗ ██╗     ██╗     ",
    " ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔══██╗██║     ██║     ",
    " ███████╗   ██║   ███████║██████╔╝█████╗  ███████║██║     ██║     ",
    " ╚════██║   ██║   ██╔══██║██╔══██╗██╔══╝  ██╔══██║██║     ██║     ",
    " ███████║   ██║   ██║  ██║██║  ██║██║     ██║  ██║███████╗███████╗",
    " ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝",
]

MENU_ITEMS = ["START GAME", "CONTROLS", "HIGH SCORES", "EXIT"]


def draw_frame(renderer, title, width=64, height=22):
    w, h = renderer.width, renderer.height
    x0 = max(0, (w - width) // 2)
    y0 = max(0, (h - height) // 2)
    renderer.box(x0, y0, width, height, C.HUD_BORDER, title)
    return x0, y0


def draw_menu(renderer, selected, high_score=0, wave_best=0, t=0.0):
    renderer.clear_buffers()
    # ambient star specks on menu
    for i in range(60):
        x = int((i * 37 + t * 8) % renderer.width)
        y = int((i * 53) % renderer.height)
        renderer.put(x, y, ".", C.STAR_DIM)
    x0, y0 = draw_frame(renderer, "STARFALL", 68, 24)
    for i, row in enumerate(LOGO):
        glow = C.BRIGHT_CYAN if int(t * 2) % 2 == 0 else C.CYAN
        renderer.text(x0 + (68 - disp_width(row)) // 2, y0 + 2 + i, row, glow)
    renderer.text_centered(y0 + 9, "T E R M I N A L   W A R", C.BRIGHT_WHITE + C.BOLD)
    # twinkling subtitle
    tw = "✦  A TERMINAL SPACE ODYSSEY  ✦"
    renderer.text_centered(y0 + 10, tw, C.BRIGHT_YELLOW if int(t * 3) % 2 == 0 else C.YELLOW)
    for i, item in enumerate(MENU_ITEMS):
        # ASCII-only selector: ▶ is double-width on some terminals and
        # shifts the centered label by a cell when it pulses.
        marker = "> " if i == selected else "  "
        label = f"{marker}{item}"
        col = C.BRIGHT_WHITE + C.BOLD if i == selected else C.HUD_TEXT
        renderer.text_centered(y0 + 13 + i * 2, label, col)
    renderer.text_centered(y0 + 22, f"BEST {high_score:08d} - WAVE {wave_best}",
                           C.BRIGHT_BLACK)
    renderer.text_centered(renderer.height - 2,
                           "W/S or Up/Down select - ENTER confirm - ESC quit",
                           C.BRIGHT_BLACK)


def draw_controls(renderer):
    x0, y0 = draw_frame(renderer, "CONTROLS", 64, 20)
    lines = [
        ("W A S D / ARROWS", "Move ship (diagonal supported)"),
        ("SPACE", "Fire cannons (hold for auto-fire)"),
        ("X / B / TAB", "NOVA CANNON special weapon"),
        ("P", "Pause / resume"),
        ("M", "Mute sound"),
        ("F1 or `", "Debug overlay (FPS/entities)"),
        ("ESC", "Quit to menu / exit"),
        ("", ""),
        ("TIP: hold SPACE while strafing. Elites dodge — lead them.", ""),
        ("TIP: NOVA clears bullets + damages everything on screen.", ""),
    ]
    for i, (k, v) in enumerate(lines):
        renderer.text(x0 + 4, y0 + 3 + i, clip_to_width(k, 18), C.BRIGHT_CYAN)
        renderer.text(x0 + 24, y0 + 3 + i, clip_to_width(v, 64 - 26), C.HUD_TEXT)
    renderer.text_centered(y0 + 18, "[ ENTER / ESC to go back ]", C.BRIGHT_YELLOW)


def draw_scores(renderer, save):
    x0, y0 = draw_frame(renderer, "HIGH SCORES", 56, 16)
    hs = save.get("high_score", 0)
    hw = save.get("highest_wave", 0)
    st = save.get("stats", {})
    renderer.text_centered(y0 + 3, f"★ HIGH SCORE  {hs:08d} ★", C.SCORE + C.BOLD)
    renderer.text_centered(y0 + 5, f"HIGHEST WAVE  {hw}", C.BRIGHT_CYAN)
    renderer.text_centered(y0 + 7, f"KILLS {st.get('kills', 0)}   BEST COMBO x{st.get('best_combo', 0)}",
                           C.HUD_TEXT)
    renderer.text_centered(y0 + 9, f"TIME FLOWN {st.get('time', 0):.0f}s   VICTORIES {st.get('victories', 0)}",
                           C.HUD_TEXT)
    renderer.text_centered(y0 + 13, "[ ENTER / ESC to go back ]", C.BRIGHT_YELLOW)


def draw_briefing(renderer, t):
    x0, y0 = draw_frame(renderer, "MISSION BRIEFING", 66, 16)
    lines = [
        "YEAR 2187. The VEX ARMADA has breached the Helios gate.",
        "",
        "You are the last STARFALL interceptor pilot.",
        "Survive 11 waves. Destroy the DREADNOUGHTs.",
        "",
        "Protect your hull. Chain kills for COMBO score.",
        "Salvage [power-ups] from wrecks. Save NOVA for swarms.",
    ]
    for i, ln in enumerate(lines):
        renderer.text(x0 + 4, y0 + 3 + i, ln, C.HUD_TEXT)
    # countdown
    n = 3 - int(t)
    if n >= 1:
        renderer.text_centered(y0 + 12, f"LAUNCH IN {n}…", C.WARNING + C.BOLD)
    else:
        renderer.text_centered(y0 + 12, "LAUNCH!", C.BRIGHT_GREEN + C.BOLD)


def draw_pause(renderer):
    w, h = renderer.width, renderer.height
    # dim: draw translucent-ish box center
    bw, bh = 40, 9
    x0, y0 = (w - bw) // 2, (h - bh) // 2
    renderer.box(x0, y0, bw, bh, C.BRIGHT_YELLOW, "PAUSED")
    renderer.text_centered(y0 + 3, "- SYSTEMS ON HOLD -", C.HUD_TEXT)
    renderer.text_centered(y0 + 5, "[P] resume - [ESC] abandon mission", C.BRIGHT_YELLOW)


def draw_game_over(renderer, score, wave, stats, last_blow, new_best, t):
    flick = int(t * 3) % 2 == 0
    col = C.BRIGHT_RED if flick else C.RED
    h = renderer.height
    cy = h // 2 - 4  # vertically centered block, adapts to terminal height
    renderer.text_centered(cy, "G A M E   O V E R", col + C.BOLD)
    renderer.text_centered(cy + 2, f"SCORE {score.score:08d}   WAVE {wave:02d}",
                           C.HUD_TEXT)
    acc = stats.accuracy() if hasattr(stats, "accuracy") else 0.0
    renderer.text_centered(cy + 4,
                           clip_to_width(
                               f"KILLS {stats.kills}   MAX COMBO x{score.best_combo}   ACC {acc:.0f}%",
                               renderer.width - 4),
                           C.HUD_TEXT)
    renderer.text_centered(cy + 6,
                           clip_to_width(
                               f"TIME {stats.time_alive:.0f}s   FINAL BLOW: {last_blow}",
                               renderer.width - 4),
                           C.BRIGHT_BLACK)
    if new_best:
        renderer.text_centered(cy + 8, "* NEW HIGH SCORE *", C.SCORE + C.BOLD)
    else:
        renderer.text_centered(cy + 8, "The stars go silent... but legends relaunch.",
                               C.BRIGHT_BLACK)
    renderer.text_centered(renderer.height - 4,
                           "[R] / [ENTER] retry   [ESC] menu", C.BRIGHT_YELLOW)


def draw_victory(renderer, score, t):
    cols = [C.BRIGHT_YELLOW, C.BRIGHT_CYAN, C.BRIGHT_MAGENTA]
    col = cols[int(t * 2) % 3]
    h = renderer.height
    cy = h // 2 - 4
    renderer.text_centered(cy, "VICTORY", col + C.BOLD)
    renderer.text_centered(cy + 2, "THE VEX ARMADA RETREATS. THE GATE HOLDS.", C.HUD_TEXT)
    renderer.text_centered(cy + 4, f"SCORE {score.score:08d} - BEST COMBO x{score.best_combo}",
                           C.SCORE)
    renderer.text_centered(cy + 6, clip_to_width(
        "Endless mode continues... how long can you hold the line?",
        renderer.width - 4), C.BRIGHT_BLACK)
    renderer.text_centered(renderer.height - 4,
                           "[ENTER] keep flying (endless)   [ESC] menu",
                           C.BRIGHT_YELLOW)
