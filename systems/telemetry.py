"""LOCAL, OPTIONAL gameplay telemetry for balance tuning.

Records per-run gameplay facts only (no identity, no personal data):
  duration, wave, result, kills, accuracy, max_combo, powerups,
  damage_taken, novas, boss_phase, death_blow.

Stored in data/telemetry.json (last 30 sessions). report() aggregates:
  sessions, avg wave reached, most common death wave, avg accuracy,
  nova-use rate — the signals Phase 21 asks for (which wave kills,
  whether specials get used, whether power-ups get collected).

Run `python -m systems.telemetry` from the project root for a report.
"""

import json
from pathlib import Path

TELEMETRY_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"
MAX_SESSIONS = 30


def load():
    try:
        with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def record(session):
    """Append one session dict; keep the file bounded. Never raises."""
    try:
        sessions = load()
        sessions.append(dict(session))
        sessions = sessions[-MAX_SESSIONS:]
        TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
    except Exception:
        pass


def report(sessions=None):
    """Aggregate balance signals. Returns {} when no data yet."""
    sessions = load() if sessions is None else list(sessions)
    if not sessions:
        return {}
    n = len(sessions)
    losses = [s for s in sessions if s.get("result") == "loss"]
    death_waves: dict = {}
    for s in losses:
        w = s.get("wave", 0)
        death_waves[w] = death_waves.get(w, 0) + 1
    top_death = None
    if death_waves:
        top_death = sorted(death_waves.items(), key=lambda kv: kv[1])[-1][0]
    return {
        "sessions": n,
        "avg_wave": round(sum(s.get("wave", 0) for s in sessions) / n, 1),
        "avg_kills": round(sum(s.get("kills", 0) for s in sessions) / n, 1),
        "avg_accuracy": round(sum(s.get("accuracy", 0) for s in sessions) / n, 1),
        "avg_max_combo": round(sum(s.get("max_combo", 0) for s in sessions) / n, 1),
        "top_death_wave": top_death,
        "nova_use_rate": round(sum(1 for s in sessions if s.get("novas", 0)) / n, 2),
        "avg_powerups": round(sum(s.get("powerups", 0) for s in sessions) / n, 1),
        "boss_reached_rate": round(sum(1 for s in sessions if s.get("boss_phase", 0)) / n, 2),
        "wins": sum(1 for s in sessions if s.get("result") == "win"),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    rep = report()
    if not rep:
        print("No telemetry yet — play a run first (data/telemetry.json).")
    else:
        print("STARFALL balance report (local sessions only):")
        for k, v in rep.items():
            print(f"  {k:18s} {v}")
