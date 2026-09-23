"""STARFALL: TERMINAL WAR — entry point.

Run:
    python main.py            (no dependencies, stdlib only)
    python main.py --debug    (start with debug overlay)

Controls:
    W/A/S/D or Arrows  move        SPACE  fire (hold)
    X / B / TAB        NOVA cannon  P      pause
    M                  mute         ESC    quit / back
    ENTER              confirm      F1/`   debug overlay
"""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from game import config as CFG
from game.engine import Game
from game.state import GameState
from rendering import sprites as S
from systems.input import InputSystem


def _supports_unicode():
    try:
        "✦".encode(sys.stdout.encoding or "utf-8")
        return True
    except Exception:
        return False


def main():
    debug = "--debug" in sys.argv
    renderer = None
    input_sys = None
    try:
        from rendering.renderer import TerminalRenderer
        renderer = TerminalRenderer()
        renderer.setup()
        # Unicode fallback for legacy code pages (e.g. cp437 without font)
        if not _supports_unicode():
            S.UNICODE_OK = False

        input_sys = InputSystem()
        game = Game(renderer, input_sys)
        game.want_exit = False
        if debug:
            game.debug = True

        w, h = renderer.refresh_size()
        game.stars.init_stars(w, h, count=max(70, w * h // 38),
                              top_reserved=CFG.HUD_HEIGHT + 1)
        game.player.reset_position(w / 2, h - 6)

        target = 1.0 / CFG.TARGET_FPS
        prev = time.perf_counter()
        fps_acc, fps_n, fps_t = 0.0, 0, 0.0

        while True:
            frame_start = time.perf_counter()
            # resize detection (cheap; rebuild buffers only on change)
            try:
                size = shutil.get_terminal_size(fallback=(120, 35))
                if size.columns != renderer.width or size.lines != renderer.height:
                    renderer.refresh_size()
                    game.stars.resize(renderer.width, renderer.height,
                                      top_reserved=CFG.HUD_HEIGHT + 1)
            except Exception:
                pass

            dt = frame_start - prev
            prev = frame_start
            # clamp huge tab-out gaps so physics doesn't explode
            dt = max(0.0001, min(0.05, dt))

            inp = input_sys.poll()
            t_update = time.perf_counter()
            game.update(dt, inp)
            t_render = time.perf_counter()
            if getattr(game, "want_exit", False):
                break
            game.render()
            t_end = time.perf_counter()
            game.logic_ms = (t_render - t_update) * 1000.0
            game.render_ms = (t_end - t_render) * 1000.0

            # fps tracking (rolling 0.5s window)
            elapsed = time.perf_counter() - frame_start
            game.frame_ms = elapsed * 1000.0
            fps_acc += dt
            fps_n += 1
            fps_t += dt
            if fps_t >= 0.5:
                game.fps = fps_n / max(0.001, fps_acc)
                fps_acc, fps_n, fps_t = 0.0, 0, 0.0

            # maintain ~60fps without busy-wait drift
            sleep_for = target - (time.perf_counter() - frame_start)
            if sleep_for > 0:
                # sleep most, spin the last ~1ms for steadier pacing
                if sleep_for > 0.002:
                    time.sleep(sleep_for - 0.001)
                    while time.perf_counter() - frame_start < target:
                        pass
                else:
                    time.sleep(max(0, sleep_for))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        try:
            if renderer is not None:
                renderer.restore()
            if input_sys is not None:
                input_sys.restore_unix()
        except Exception:
            pass
        print(f"\nSTARFALL crashed gracefully: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            if renderer is not None:
                renderer.restore()
            if input_sys is not None:
                input_sys.restore_unix()
        except Exception:
            pass
    print("\nThanks for flying, pilot. The gate holds because of you. ✦")


if __name__ == "__main__":
    main()
