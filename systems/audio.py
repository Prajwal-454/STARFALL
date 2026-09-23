"""Retro sound effects — single worker thread, throttled, non-fatiguing.

Design notes (shmup audio theory):
  * Repetitive sounds (laser/hit) are the #1 fatigue source. They are
    rate-limited and kept very short (<40ms) so holding SPACE doesn't
    produce a piercing 60%-duty-cycle drone.
  * Only ONE daemon worker owns winsound, fed by a bounded queue. The old
    thread-per-play design stacked overlapping Beeps at the OS level and
    caused stutter + harshness.
  * Priority: laser/hit may be dropped when busy; hurt/warning/nova/
    gameover/victory always play (gameplay-critical feedback).
  * Sequences use short descending pitches + silence gaps instead of long
    flat square waves, which reads as "soft retro" on winsound.Beep
    (which has no volume control).
100% safe to fail: no winsound / muted => silent no-op, never blocks loop.
Toggle with M.
"""

import queue
import threading
import time

MUTED_DEFAULT = False

# Min seconds between repeats of the same sound (anti-spam).
_MIN_INTERVAL = {
    "laser": 0.07,
    "laser2": 0.07,
    "hit": 0.06,
    "explosion": 0.12,
    "big_explosion": 0.20,
    "powerup": 0.15,
    "nova": 0.30,
    "warning": 0.50,
    "hurt": 0.20,
    "shield": 0.20,
    "menu": 0.08,
    "gameover": 0.50,
    "victory": 0.50,
    "wave": 0.30,
}

# Sounds that may be dropped when the queue is busy (non-critical).
_DROPPABLE = {"laser", "laser2", "hit", "shield"}

_MAX_QUEUE = 8


class AudioSystem:
    def __init__(self, muted=False):
        self.muted = muted
        self._winsound = None
        try:
            import winsound  # type: ignore
            self._winsound = winsound
        except Exception:
            self._winsound = None
        self._queue: "queue.Queue" = queue.Queue(maxsize=_MAX_QUEUE)
        self._last: dict = {}
        self._worker_started = False
        self._lock = threading.Lock()

    def toggle(self):
        self.muted = not self.muted
        return self.muted

    def play(self, name):
        if self.muted or self._winsound is None:
            return
        now = time.monotonic()
        min_gap = _MIN_INTERVAL.get(name, 0.05)
        last = self._last.get(name, 0.0)
        if now - last < min_gap:
            return  # throttle machine-gun repeats (laser/hit spam)
        self._last[name] = now
        seq = self._sequence(name)
        if not seq:
            return
        self._ensure_worker()
        try:
            self._queue.put_nowait(seq)
        except queue.Full:
            # Busy: drop non-critical blips, keep critical feedback.
            if name in _DROPPABLE:
                return
            try:
                self._queue.get_nowait()  # make room for critical sound
                self._queue.put_nowait(seq)
            except Exception:
                pass

    def _ensure_worker(self):
        with self._lock:
            if self._worker_started:
                return
            self._worker_started = True
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()

    def _worker(self):
        while True:
            try:
                seq = self._queue.get()
            except Exception:
                return
            try:
                self._beep_seq(seq)
                # tiny breath between sounds avoids harsh back-to-back squares
                time.sleep(0.012)
            except Exception:
                pass

    def _sequence(self, name):
        # (freq_hz, duration_ms). freq 0 = silence gap. Kept short + soft:
        # laser/hit <40ms ticks, explosions descending, jingles quick.
        return {
            "laser": [(920, 35)],
            "laser2": [(700, 35)],
            "hit": [(180, 60)],
            "explosion": [(110, 120), (70, 150)],
            "big_explosion": [(100, 150), (70, 180), (50, 220)],
            "powerup": [(523, 60), (659, 60), (784, 90)],
            "nova": [(180, 90), (360, 90), (720, 140)],
            "warning": [(520, 120), (0, 60), (520, 120)],
            "hurt": [(240, 100), (150, 130)],
            "shield": [(800, 60)],
            "menu": [(650, 40)],
            "gameover": [(330, 150), (260, 150), (180, 250)],
            "victory": [(523, 90), (659, 90), (784, 90), (1046, 180)],
            "wave": [(440, 70), (660, 100)],
        }.get(name, [])

    def _beep_seq(self, seq):
        try:
            for freq, dur in seq:
                if freq <= 0:
                    time.sleep(dur / 1000.0)
                else:
                    self._winsound.Beep(freq, dur)  # type: ignore
        except Exception:
            pass
