#!/usr/bin/env python3
"""
F1 Dashboard — Season Results Backfill
======================================
Fetches race results for all completed rounds (1–8) from the jolpi.ca Ergast
mirror and merges them into data/season_results.json, preserving the existing
R9 entry and matching the exact JSON shape that generate_pages.py expects.

Run from the repo root:
    python3 scripts/backfill_season_results.py
"""

import json
import urllib.request
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(ROOT, "data")
SEASON_RESULTS_PATH = os.path.join(DATA_DIR, "season_results.json")

ERGAST_BASE = "https://api.jolpi.ca/ergast/f1"
SEASON = "2026"

# Rounds 1-8 need backfilling; R9 (British GP) is already in the file.
BACKFILL_ROUNDS = list(range(1, 9))


def fetch_round(round_num):
    """Fetch a single round's results from jolpi.ca and convert to our format."""
    url = f"{ERGAST_BASE}/{SEASON}/{round_num}/results.json"
    req = urllib.request.Request(url, headers={"User-Agent": "F1Dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return None

    race = races[0]
    circuit = race.get("Circuit", {})

    # Convert each result entry
    converted = []
    for res in race.get("Results", []):
        driver = res.get("Driver", {})
        constructor = res.get("Constructor", {})
        fastest_lap = res.get("FastestLap", {})

        # Map Ergast status to our conventions
        raw_status = res.get("status", "")
        pos_text = res.get("positionText", "")
        if raw_status == "Finished":
            status = "Finished"
        elif raw_status == "Lapped":
            status = "Lapped"
        elif raw_status == "Did not start":
            status = "Did not start"
        elif raw_status == "Retired":
            status = "Retired"
        elif pos_text in ("R", "W", "D", "F", "N"):
            status = "Retired"
        else:
            status = raw_status or "Retired"

        # Time: winner gets total time; others get gap or empty
        time_obj = res.get("Time", {})
        time_str = ""
        if time_obj:
            time_str = time_obj.get("time", "")

        # FastestLap: keep rank, lap, time
        fl = {}
        if fastest_lap:
            fl = {
                "rank": fastest_lap.get("rank", ""),
                "lap": fastest_lap.get("lap", ""),
            }
            fl_time = fastest_lap.get("Time", {})
            if fl_time:
                fl["time"] = fl_time.get("time", "")

        result_entry = {
            "position": res.get("position", ""),
            "grid": res.get("grid", ""),
            "driver": {
                "code": driver.get("code", ""),
                "givenName": driver.get("givenName", ""),
                "familyName": driver.get("familyName", ""),
                "nationality": driver.get("nationality", ""),
            },
            "constructor": constructor.get("name", ""),
            "laps": res.get("laps", ""),
            "time": time_str,
            "status": status,
            "fastestLap": fl if fl else None,
        }
        converted.append(result_entry)

    race_obj = {
        "round": str(race.get("round", round_num)),
        "raceName": race.get("raceName", ""),
        "date": race.get("date", ""),
        "circuit": {
            "circuitName": circuit.get("circuitName", ""),
            "Location": {
                "locality": circuit.get("Location", {}).get("locality", ""),
                "country": circuit.get("Location", {}).get("country", ""),
            },
        },
        "results": converted,
    }
    return race_obj


def main():
    # Load existing season_results.json
    with open(SEASON_RESULTS_PATH, encoding="utf-8") as f:
        season_data = json.load(f)

    existing_rounds = {r["round"] for r in season_data.get("races", [])}
    print(f"Existing rounds in archive: {sorted(existing_rounds)}")

    new_races = []
    for rnd in BACKFILL_ROUNDS:
        r_str = str(rnd)
        if r_str in existing_rounds:
            print(f"  R{rnd}: already present, skipping")
            continue
        print(f"  R{rnd}: fetching...", end=" ", flush=True)
        race_obj = fetch_round(rnd)
        if race_obj is None:
            print("NO DATA")
            continue
        print(f"{race_obj['raceName']} — {len(race_obj['results'])} drivers")
        new_races.append(race_obj)

    if not new_races:
        print("Nothing to backfill.")
        return

    # Insert in round order
    all_races = season_data.get("races", []) + new_races
    all_races.sort(key=lambda r: int(str(r.get("round", "0")).strip() or 0))

    season_data["races"] = all_races
    season_data["season"] = SEASON

    # Write back
    with open(SEASON_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(season_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nDone! season_results.json now has {len(all_races)} races (rounds {', '.join(r['round'] for r in all_races)})")


if __name__ == "__main__":
    main()
