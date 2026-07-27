#!/usr/bin/env python3
"""
Verify results.json in the repo against the live jolpi.ca API.
Exits 1 on any mismatch, 0 if all positions match.

Usage:
    python3 scripts/verify_results.py [--repo /tmp/f1-dashboard]

This script was created after a bug where Sainz was P12 in the repo
but P17 in the API (he was Lapped — 51 laps vs 52). The pipeline had
incorrectly placed a lapped driver ahead of drivers who completed
more laps.
"""
import json
import subprocess
import sys
import os

REPO_DEFAULT = "/tmp/f1-dashboard"
API_URL = "https://api.jolpi.ca/ergast/f1/current/last/results.json"

def main():
    repo = sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else REPO_DEFAULT
    results_path = os.path.join(repo, "data/results.json")

    # Fetch live API data
    result = subprocess.run(["curl", "-s", API_URL], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"ERROR: Could not fetch from {API_URL}")
        sys.exit(2)

    api_data = json.loads(result.stdout)
    api_race = api_data["MRData"]["RaceTable"]["Races"][0]

    # Load repo data
    with open(results_path) as f:
        repo_data = json.load(f)

    # Race name check
    api_race_name = api_race["raceName"]
    repo_race_name = repo_data.get("raceName", "?")
    if api_race_name != repo_race_name:
        print(f"WARNING: Repo has '{repo_race_name}' but API has '{api_race_name}'")
        print("  (Repo may not have been updated to the latest race yet)")

    # Build API driver map by position
    api_by_pos = {}
    for r in api_race["Results"]:
        api_by_pos[r["position"]] = {
            "name": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "laps": r["laps"],
            "status": r["status"],
        }

    mismatches = []
    for repo_r in repo_data["results"]:
        pos = repo_r["position"]
        repo_name = f"{repo_r['driver']['givenName']} {repo_r['driver']['familyName']}"
        repo_laps = repo_r.get("laps", "?")
        repo_status = repo_r.get("status", "?")

        if pos not in api_by_pos:
            mismatches.append(f"P{pos}: {repo_name} — not found in API results")
            continue

        api = api_by_pos[pos]
        if repo_name != api["name"]:
            mismatches.append(f"P{pos}: repo={repo_name} vs API={api['name']}")
        elif repo_laps != api["laps"]:
            mismatches.append(f"P{pos}: {repo_name} — laps repo={repo_laps} vs API={api['laps']}")
        elif repo_status != api["status"]:
            mismatches.append(f"P{pos}: {repo_name} — status repo={repo_status} vs API={api['status']}")

    if mismatches:
        print(f"❌ {len(mismatches)} MISMATCH(ES) found:\n")
        for m in mismatches:
            print(f"  {m}")
        print(f"\nRepo race: {repo_race_name} | API race: {api_race_name}")
        sys.exit(1)
    else:
        n = len(repo_data["results"])
        print(f"✅ All {n} positions match the API ({api_race_name}). No mismatches.")
        sys.exit(0)


if __name__ == "__main__":
    main()
