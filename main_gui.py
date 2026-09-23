"""STARFALL (GUI) — entry point. Run from CMD with:  python main_gui.py

Same game, same saves (data/save.json), rendered with pygame instead of
ANSI: crisp pixel-art ships, real window, no font/codepage issues.
Controls are identical to the terminal version, plus:
    F11             toggle fullscreen
    --fullscreen    start in fullscreen
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pygame

from game import config as CFG
from game.engine import Game
from ui.pygame_frontend import PygameInput, PygameRenderer


def main():
    renderer = PygameRenderer()
    renderer.setup(fullscreen="--fullscreen" in sys.argv)
    input_sys = PygameInput()
    try:
        game = Game(renderer, input_sys)
        game.want_exit = False
        game.stars.init_stars(renderer.width, renderer.height,
                              count=max(70, renderer.width * renderer.height // 38),
                              top_reserved=CFG.HUD_HEIGHT + 1)
        game.player.reset_position(renderer.width / 2, renderer.height - 6)

        clock = pygame.time.Clock()
        prev = time.perf_counter()
        while True:
            dt = clock.tick(CFG.TARGET_FPS) / 1000.0 or 1.0 / CFG.TARGET_FPS
            dt = max(0.0001, min(0.05, dt))
            prev = time.perf_counter()

            inp = input_sys.poll()
            if input_sys.closed:
                break
            if input_sys.toggle_fullscreen:
                renderer.set_fullscreen(not renderer.fullscreen)
            t_update = time.perf_counter()
            game.update(dt, inp)
            t_render = time.perf_counter()
            if getattr(game, "want_exit", False):
                break
            game.render()
            t_end = time.perf_counter()
            game.logic_ms = (t_render - t_update) * 1000.0
            game.render_ms = (t_end - t_render) * 1000.0
            game.fps = clock.get_fps() or CFG.TARGET_FPS
            game.frame_ms = dt * 1000.0
            _ = prev
    except KeyboardInterrupt:
        pass
    finally:
        try:
            renderer.restore()
        except Exception:
            pass
    print("\nThanks for flying, pilot. The gate holds because of you.")


if __name__ == "__main__":
    main()
