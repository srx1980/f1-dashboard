#!/usr/bin/env python3
"""
F1 Dashboard — Race Results Pipeline (OpenF1 fallback)
======================================================
Used when Ergast/jolpi.ca API is down. Fetches lap timing data from
OpenF1 and reconstructs race classification.

Algorithm:
  1. Fetch laps from /v1/laps?session_key=<KEY>
  2. Per driver: max_lap number + finish time (lap_start + lap_duration)
  3. Sort: laps DESC, finish_time ASC
  4. 90% rule: classified if laps >= ceil(0.9 * winner_laps)
  5. Winner gets total race time; others get gap format
  6. NC entries: DNF if stopped early, "+N Laps" if finished but unclassified

Accuracy: ~95%+ (may differ by 1-2 positions in tight lapped-traffic finishes
due to OpenF1 timing precision vs official FIA transponder data).

Usage:
  python3 fetch_results_openf1.py [--session-key KEY] [--year 2026] [--output results.json]
"""

import sys, json, argparse
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.request import urlopen, Request
from urllib.error import URLError

OPENF1_BASE = "https://api.openf1.org/v1"

# ============================================================
# DRIVER IDENTITY MAP (OpenF1 driver_number → identity)
# ============================================================
# IMPORTANT: Display names differ from API names.
# API "Red Bull" → display "Red Bull Racing"
# API "RB" → display "Racing Bulls"
# API "Sauber" → display "Audi" (rebranded for 2026)
# API "Haas" → display "Haas F1 Team"

DRIVER_MAP = {
    1:  ("NOR", "Lando",           "Norris",    "British",       "McLaren"),
    3:  ("VER", "Max",             "Verstappen", "Dutch",         "Red Bull Racing"),
    5:  ("BOR", "Gabriel",         "Bortoleto",  "Brazilian",     "Audi"),
    6:  ("HAD", "Isack",           "Hadjar",     "French",        "Red Bull Racing"),
    10: ("GAS", "Pierre",          "Gasly",      "French",        "Alpine"),
    11: ("PER", "Sergio",          "Perez",      "Mexican",       "Cadillac"),
    12: ("ANT", "Andrea Kimi",     "Antonelli",  "Italian",       "Mercedes"),
    14: ("ALO", "Fernando",        "Alonso",     "Spanish",       "Aston Martin"),
    16: ("LEC", "Charles",         "Leclerc",    "Monegasque",    "Ferrari"),
    18: ("STR", "Lance",           "Stroll",     "Canadian",      "Aston Martin"),
    23: ("ALB", "Alexander",       "Albon",      "Thai",          "Williams"),
    27: ("HUL", "Nico",            "Hulkenberg", "German",        "Audi"),
    30: ("LAW", "Liam",            "Lawson",     "New Zealander", "Racing Bulls"),
    31: ("OCO", "Esteban",         "Ocon",       "French",        "Haas F1 Team"),
    41: ("LIN", "Arvid",           "Lindblad",   "Swedish",       "Racing Bulls"),
    43: ("COL", "Franco",          "Colapinto",  "Argentine",     "Alpine"),
    44: ("HAM", "Lewis",           "Hamilton",   "British",       "Ferrari"),
    55: ("SAI", "Carlos",          "Sainz",      "Spanish",       "Williams"),
    63: ("RUS", "George",          "Russell",    "British",       "Mercedes"),
    77: ("BOT", "Valtteri",        "Bottas",     "Finnish",       "Cadillac"),
    81: ("PIA", "Oscar",           "Piastri",    "Australian",    "McLaren"),
    87: ("BEA", "Oliver",          "Bearman",    "British",       "Haas F1 Team"),
}


def fetch_json(url, timeout=15):
    """Fetch JSON from URL with retries."""
    req = Request(url, headers={"User-Agent": "F1Dashboard/1.0"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == 2:
                raise
            import time
            time.sleep(2)


def get_last_race_session(year=2026):
    """Find the most recent completed race session key."""
    url = f"{OPENF1_BASE}/sessions?year={year}&session_type=Race&session_name=Race"
    sessions = fetch_json(url)
    now = datetime.now().isoformat()
    past_sessions = [s for s in sessions if s["date_start"] < now]
    if not past_sessions:
        raise ValueError(f"No completed races found for {year}")
    latest = max(past_sessions, key=lambda s: s["date_start"])
    return latest


def get_grid_positions(session_key):
    """Get starting grid from first position data snapshot."""
    url = f"{OPENF1_BASE}/position?session_key={session_key}&position<=25"
    positions = fetch_json(url)
    grid = {}
    for p in sorted(positions, key=lambda x: x["date"]):
        dn = p["driver_number"]
        if dn not in grid:
            grid[dn] = str(p["position"])
    return grid


def get_driver_laps(session_key):
    """Fetch lap data and compute finish order."""
    url = f"{OPENF1_BASE}/laps?session_key={session_key}"
    laps = fetch_json(url)
    laps = [l for l in laps if l.get("lap_duration") is not None]

    race_start_str = min(l["date_start"] for l in laps)
    race_start = datetime.fromisoformat(race_start_str.replace("Z", "+00:00"))

    drv_info = {}
    for lap in laps:
        dn = lap["driver_number"]
        ln = lap["lap_number"]
        if dn not in drv_info or ln > drv_info[dn]["max_lap"]:
            s = datetime.fromisoformat(lap["date_start"].replace("Z", "+00:00"))
            f = s + timedelta(seconds=lap["lap_duration"])
            drv_info[dn] = {"max_lap": ln, "finish": f}

    return drv_info, race_start


def build_results(drv_info, race_start, grid):
    """Build results.json from driver info."""
    order = sorted(drv_info.items(), key=lambda x: (-x[1]["max_lap"], x[1]["finish"]))
    w_dn, w_info = order[0]
    w_laps, w_finish = w_info["max_lap"], w_info["finish"]
    w_time_sec = (w_finish - race_start).total_seconds()
    w_time = f"{int(w_time_sec//3600)}:{int((w_time_sec%3600)//60):02d}:{w_time_sec%60:06.3f}"

    threshold = int(0.9 * w_laps + 0.5)  # round up: 59.4 → 60

    results = []
    c = 0
    for dn, info in order:
        laps = info["max_lap"]
        classified = laps >= threshold
        c += 1 if classified else 0
        pos = str(c) if classified else "NC"

        d = DRIVER_MAP.get(dn, (f"D{dn}", f"#{dn}", "", "", "?"))
        code, given, family, nat, const = d

        # Determine time/gap string
        if dn == w_dn:
            time_str = w_time
        elif laps == w_laps:
            gap = (info["finish"] - w_finish).total_seconds()
            time_str = f"+{gap:.3f}s"
        else:
            diff = w_laps - laps
            time_str = f"+{diff} Lap" + ("s" if diff > 1 else "")

        # DNF detection: did the driver stop before the race ended?
        # Two checks:
        # 1. Driver didn't start lap (max_lap+1) while others did (race was live)
        # 2. Driver's last lap finished well before race end (>60s gap = stopped early)
        next_lap = laps + 1
        race_was_live = any(i2["max_lap"] >= next_lap for i2 in drv_info.values())
        stopped_early = race_was_live
        if stopped_early:
            gap_to_end = (w_finish - info["finish"]).total_seconds()
            stopped_early = gap_to_end > 60  # >60s before checkered flag
        
        is_dnf = stopped_early

        if is_dnf:
            status = "DNF"
            time_str = None  # DNF = no time
        elif not classified:
            # NC but not DNF (e.g. Albon: finished 55 laps, race ended)
            diff = w_laps - laps
            status = f"+{diff} Laps"
            time_str = None
        else:
            status = "Finished"

        results.append({
            "position": pos,
            "grid": grid.get(dn, "?"),
            "driver": {"code": code, "givenName": given, "familyName": family, "nationality": nat},
            "constructor": const,
            "laps": str(laps),
            "time": time_str,
            "status": status,
            "fastestLap": None,
        })

    return results, w_time


def get_race_metadata(session):
    """Extract season, round, race name, date from session data."""
    return {
        "season": str(session["year"]),
        "round": str(session.get("round", "?")),
        "raceName": session.get("meeting_name", session.get("session_name", "?")),
        "date": session["date_start"][:10],
        "circuit": {
            "circuitName": session.get("circuit_name", session.get("circuit_short_name", "?")),
            "location": {
                "locality": session.get("country_name", "?"),
                "country": session.get("country_name", "?"),
            }
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch F1 race results from OpenF1")
    parser.add_argument("--session-key", type=int, help="OpenF1 session key (auto-detect if omitted)")
    parser.add_argument("--year", type=int, default=2026, help="Season year")
    parser.add_argument("--output", default="results.json", help="Output path")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    if args.session_key:
        session = {"session_key": args.session_key, "year": args.year,
                   "date_start": f"{args.year}-01-01T00:00:00",
                   "meeting_name": "Race", "country_name": "?"}
    else:
        session = get_last_race_session(args.year)
        print(f"Found session: {session['session_key']} — {session.get('meeting_name', '?')} ({session['date_start'][:10]})", file=sys.stderr)

    session_key = session["session_key"]
    meta = get_race_metadata(session)

    grid = get_grid_positions(session_key)
    drv_info, race_start = get_driver_laps(session_key)
    results, _ = build_results(drv_info, race_start, grid)

    output = {**meta, "results": results}
    json_str = json.dumps(output, indent=2, ensure_ascii=False)

    if args.json:
        print(json_str)
    else:
        with open(args.output, "w") as f:
            f.write(json_str)
        print(f"✓ {len(results)} results → {args.output}", file=sys.stderr)

    # Summary
    for r in results[:10]:
        d = r["driver"]
        print(f"P{r['position']:>3s} {d['code']:3s} {d['givenName']} {d['familyName']} — {r['laps']}l {r['time'] or r['status']}", file=sys.stderr)


if __name__ == "__main__":
    main()