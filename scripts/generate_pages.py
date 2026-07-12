#!/usr/bin/env python3
"""
F1 Dashboard - Static Page Generator (SEO expansion)
====================================================
Generates one static HTML page per driver and per constructor from the JSON
data in /data, plus a full sitemap.xml. These pages are plain static HTML
(no client-side rendering) so search engines index them directly.

This is the "Hermes pipeline" step for the Extra Pages roadmap: run it after
each Grand Prix (once data/*.json is refreshed) to regenerate every subpage.

Usage (from the repo root):
    python scripts/generate_pages.py

Outputs:
    drivers/<code>.html        (e.g. drivers/ant.html)
    teams/<slug>.html          (e.g. teams/red-bull-racing.html)
    sitemap.xml                (homepage + all subpages + static extra pages)

No third-party dependencies. Vanilla HTML/CSS/JS site constraints are kept:
the generated files are static and reference the existing css/style.css.
"""

import json
import os
import re
import html
from datetime import date, datetime

# --------------------------------------------------------------------------- #
# Paths & config
# --------------------------------------------------------------------------- #

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(ROOT, "data")
DRIVERS_DIR = os.path.join(ROOT, "drivers")
TEAMS_DIR = os.path.join(ROOT, "teams")

BASE_URL = "https://srx1980.github.io/f1-dashboard/"
OG_IMAGE = BASE_URL + "assets/og-image.png"
ASSET_VERSION = "11"  # keep in sync with the ?v= on index.html assets

# Extra hand-authored static pages that should also appear in the sitemap.
STATIC_PAGES = ["2026-regulations.html"]

# Team accent colors keyed by the exact constructor names used in the data.
TEAM_COLORS = {
    "Mercedes": "#27f4d2",
    "Ferrari": "#e8002d",
    "McLaren": "#ff8000",
    "Red Bull Racing": "#3671c6",
    "Alpine": "#0093cc",
    "Racing Bulls": "#6692ff",
    "Haas F1 Team": "#b6babd",
    "Williams": "#64c4ff",
    "Audi": "#00a19b",
    "Aston Martin": "#229971",
    "Cadillac": "#c69a4e",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def e(value):
    """HTML-escape a value for safe interpolation."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def slugify(name):
    """'Red Bull Racing' -> 'red-bull-racing'."""
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def driver_slug(driver):
    """Prefer the 3-letter code; fall back to the full name."""
    code = (driver.get("code") or "").strip()
    if code:
        return code.lower()
    return slugify(f"{driver.get('givenName', '')} {driver.get('familyName', '')}")


def team_color(name):
    return TEAM_COLORS.get(name, "#888")


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def full_name(driver):
    return f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()


# --------------------------------------------------------------------------- #
# Shared HTML fragments
# --------------------------------------------------------------------------- #

def render_head(title, description, canonical_path, prefix, json_ld):
    """
    prefix: relative path back to the repo root ('../' for /drivers, /teams).
    canonical_path: path relative to the site root (e.g. 'drivers/ant.html').
    json_ld: list of dicts serialized as separate <script> blocks.
    """
    canonical = BASE_URL + canonical_path
    ld_blocks = "\n".join(
        '  <script type="application/ld+json">\n'
        + json.dumps(block, ensure_ascii=False, indent=2)
        + "\n  </script>"
        for block in json_ld
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}" />
  <meta name="theme-color" content="#0a0a0a" />
  <link rel="canonical" href="{e(canonical)}" />

  <!-- Open Graph -->
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(description)}" />
  <meta property="og:image" content="{e(OG_IMAGE)}" />
  <meta property="og:url" content="{e(canonical)}" />
  <meta property="og:site_name" content="F1 Dashboard" />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{e(title)}" />
  <meta name="twitter:description" content="{e(description)}" />
  <meta name="twitter:image" content="{e(OG_IMAGE)}" />

  <link rel="icon" href="{prefix}assets/favicon.ico" sizes="any" />
  <link rel="icon" type="image/png" href="{prefix}assets/favicon.png" />
  <link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png" />
  <link rel="stylesheet" href="{prefix}css/style.css?v={ASSET_VERSION}" />

{ld_blocks}
</head>"""


def render_header(prefix):
    """Sticky site header/brand, matching index.html. Nav points home."""
    return f"""  <header class="hero" id="top">
    <div class="container hero__inner">
      <a class="hero__brand" href="{prefix}index.html" aria-label="F1 Dashboard home">
        <span class="hero__mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 17.5a8 8 0 1 1 16 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M12 4.5v2M5.4 7.4l1.4 1.4M18.6 7.4l-1.4 1.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            <path d="M12 17.5 16.5 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="17.5" r="1.9" fill="currentColor"/>
          </svg>
        </span>
        <div>
          <h2 class="hero__title">F1 Dashboard</h2>
          <p class="hero__season">2026 Season</p>
        </div>
      </a>

      <nav class="nav" aria-label="Site navigation">
        <a href="{prefix}index.html#upcoming">Upcoming</a>
        <a href="{prefix}index.html#standings">Standings</a>
        <a href="{prefix}index.html#results">Results</a>
        <a href="{prefix}index.html#calendar">Calendar</a>
        <a href="{prefix}2026-regulations.html">Regulations</a>
      </nav>
    </div>
  </header>"""


def render_breadcrumb(prefix, section_label, section_href, current):
    return f"""      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="{prefix}index.html">Home</a>
        <span aria-hidden="true">/</span>
        <a href="{e(section_href)}">{e(section_label)}</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{e(current)}</span>
      </nav>"""


def render_footer(prefix):
    return f"""  <footer class="footer">
    <div class="container">
      <p><a href="{prefix}index.html">&larr; Back to the F1 Dashboard</a></p>
      <p>F1 Dashboard - unofficial, fan-made. Not affiliated with Formula 1.</p>
    </div>
  </footer>

  <!-- Analytics: GoatCounter (privacy-friendly, no cookies) -->
  <script data-goatcounter="https://f1dashboard2026.goatcounter.com/count"
          async src="//gc.zgo.at/count.js"></script>
</body>
</html>"""


def delta_markup(grid, pos):
    """Grid -> finish position-change indicator, mirroring the dashboard."""
    try:
        g, p = int(grid), int(pos)
    except (TypeError, ValueError):
        return ""
    d = g - p
    if d > 0:
        return f' <span class="delta delta--up" title="Gained {d}">&#9650;{d}</span>'
    if d < 0:
        return f' <span class="delta delta--down" title="Lost {-d}">&#9660;{-d}</span>'
    return ' <span class="delta delta--same" title="No change">&#9644;</span>'


# --------------------------------------------------------------------------- #
# Driver pages
# --------------------------------------------------------------------------- #

def build_driver_page(entry, season, results, schedule, season_results):
    driver = entry.get("driver", {})
    name = full_name(driver)
    code = (driver.get("code") or "").upper()
    team = entry.get("constructor", "")
    color = team_color(team)
    slug = driver_slug(driver)
    tslug = slugify(team)

    nationality = driver.get("nationality", "")
    number = driver.get("permanentNumber", "")
    position = entry.get("position", "")
    points = entry.get("points", "0")
    wins = entry.get("wins", "0")

    title = f"{name} - {season} F1 Season Stats, Results & Standing | F1 Dashboard"
    description = (
        f"{name} ({code}) {season} Formula 1 season: driving for {team}, "
        f"currently P{position} in the drivers' championship with {points} points "
        f"and {wins} win(s). Latest race result and full {season} results, race by race."
    )
    canonical_path = f"drivers/{slug}.html"

    # --- Latest race result for this driver ---
    latest = next((r for r in results.get("results", [])
                   if (r.get("driver", {}).get("code") or "").upper() == code), None)
    latest_html = '<p class="state">No race result available yet.</p>'
    if latest:
        finished = (latest.get("status", "").lower() == "finished")
        pos = latest.get("position", "")
        grid = latest.get("grid", "")
        time_or_status = latest.get("time") or "" if finished else latest.get("status", "")
        fl = latest.get("fastestLap") or {}
        fl_txt = fl.get("time", "-") if fl else "-"
        race_name = results.get("raceName", "")
        race_date = results.get("date", "")
        latest_html = f"""          <div class="table-wrap card">
            <table class="table">
              <thead>
                <tr><th>Race</th><th class="num">Grid</th><th class="num">Finish</th><th>Result</th><th>Fastest Lap</th></tr>
              </thead>
              <tbody>
                <tr style="--team:{color}">
                  <td>{e(race_name)} <span class="code">{e(race_date)}</span></td>
                  <td class="num">{e(grid)}{delta_markup(grid, pos)}</td>
                  <td class="num">{e(pos)}</td>
                  <td>{'' if finished else '<span class="status--dnf">'}{e(time_or_status) or '-'}{'' if finished else '</span>'}</td>
                  <td>{e(fl_txt)}</td>
                </tr>
              </tbody>
            </table>
          </div>"""

    # --- Full season results, race by race (from season_results.json) ---
    # season_results.races[] holds one results.json-shaped object per completed
    # round; Hermes appends the latest race after each GP.
    season_rows = []
    for race in season_results.get("races", []):
        row = next((r for r in race.get("results", [])
                    if (r.get("driver", {}).get("code") or "").upper() == code), None)
        if row:
            season_rows.append((race, row))
    season_rows.sort(key=lambda pair: int(str(pair[0].get("round", "0")).strip() or 0))

    if season_rows:
        rows_html = []
        for race, row in season_rows:
            status = row.get("status", "")
            finished = status.lower() == "finished"
            if finished:
                result_cell = e(row.get("time") or "-")
            else:
                cls = "gap" if status.lower() == "lapped" else "status--dnf"
                result_cell = f'<span class="{cls}">{e(status) or "-"}</span>'
            rows_html.append(f"""                <tr style="--team:{color}">
                  <td class="num">{e(race.get("round"))}</td>
                  <td>{e(race.get("raceName"))}</td>
                  <td class="num">{e(row.get("grid"))}{delta_markup(row.get("grid"), row.get("position"))}</td>
                  <td class="num">{e(row.get("position"))}</td>
                  <td>{result_cell}</td>
                </tr>""")
        results_table_html = f"""          <div class="table-wrap card">
            <table class="table">
              <thead>
                <tr><th class="num">Rnd</th><th>Race</th><th class="num">Grid</th><th class="num">Finish</th><th>Result</th></tr>
              </thead>
              <tbody>
{chr(10).join(rows_html)}
              </tbody>
            </table>
          </div>"""
    else:
        results_table_html = '<p class="state">Full {} results will appear here race by race.</p>'.format(season)

    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": name,
            "nationality": nationality,
            "jobTitle": "Formula 1 Driver",
            "affiliation": {"@type": "SportsTeam", "name": team},
            "url": BASE_URL + canonical_path,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
                {"@type": "ListItem", "position": 2, "name": "Drivers",
                 "item": BASE_URL + "index.html#standings"},
                {"@type": "ListItem", "position": 3, "name": name,
                 "item": BASE_URL + canonical_path},
            ],
        },
    ]

    page = f"""{render_head(title, description, canonical_path, '../', json_ld)}
<body class="subpage">
  <a class="skip-link" href="#main">Skip to content</a>
{render_header('../')}

  <main class="container" id="main">
    <section class="section">
{render_breadcrumb('../', 'Drivers', '../index.html#standings', name)}

      <header class="profile" style="--team:{color}">
        <div class="profile__id">
          <h1 class="profile__name">{e(name)}</h1>
          <span class="profile__code">{e(code)}</span>
        </div>
        <p class="profile__meta">
          <a class="entity-link" href="../teams/{tslug}.html">{e(team)}</a>
          &middot; {e(nationality)}{f' &middot; #{e(number)}' if number else ''}
        </p>
      </header>

      <div class="stats">
        <div class="stat"><span class="stat__label">Championship</span><span class="stat__value">P{e(position)}</span></div>
        <div class="stat"><span class="stat__label">Points</span><span class="stat__value">{e(points)}</span></div>
        <div class="stat"><span class="stat__label">Wins</span><span class="stat__value">{e(wins)}</span></div>
      </div>

      <div class="section__head"><h2 class="section__title">Latest Race Result</h2></div>
{latest_html}

      <div class="section__head"><h2 class="section__title">{season} Results</h2></div>
{results_table_html}
    </section>
  </main>

{render_footer('../')}
"""
    return slug, page


# --------------------------------------------------------------------------- #
# Team pages
# --------------------------------------------------------------------------- #

def build_team_page(entry, season, standings, results, schedule):
    team = entry.get("constructor", "")
    color = team_color(team)
    slug = slugify(team)
    nationality = entry.get("nationality", "")
    position = entry.get("position", "")
    points = entry.get("points", "0")
    wins = entry.get("wins", "0")

    title = f"{team} - {season} F1 Season Results, Drivers & Standing | F1 Dashboard"
    description = (
        f"{team} in the {season} Formula 1 season: P{position} in the "
        f"constructors' championship with {points} points and {wins} win(s). "
        f"Current drivers, latest race result, and season wins."
    )
    canonical_path = f"teams/{slug}.html"

    # Drivers on this team (from the driver standings).
    team_drivers = [d for d in standings.get("driverStandings", [])
                    if d.get("constructor") == team]
    driver_links = "\n".join(
        f'          <li><a class="entity-link" href="../drivers/{driver_slug(d.get("driver", {}))}.html">'
        f'{e(full_name(d.get("driver", {})))}</a> '
        f'<span class="code">{e((d.get("driver", {}).get("code") or "").upper())}</span> '
        f'&middot; P{e(d.get("position"))} &middot; {e(d.get("points"))} pts</li>'
        for d in team_drivers
    ) or '          <li class="state">No drivers listed.</li>'

    # Latest race rows for the team's drivers.
    team_rows = [r for r in results.get("results", []) if r.get("constructor") == team]
    if team_rows:
        body = "\n".join(
            f"""                <tr style="--team:{color}">
                  <td><span class="driver__name">{e(full_name(r.get("driver", {})))}</span> <span class="code">{e((r.get("driver", {}).get("code") or "").upper())}</span></td>
                  <td class="num">{e(r.get("grid"))}{delta_markup(r.get("grid"), r.get("position"))}</td>
                  <td class="num">{e(r.get("position"))}</td>
                  <td>{('' if r.get("status", "").lower() == "finished" else '<span class="status--dnf">')}{e(r.get("time") or r.get("status")) or '-'}{('' if r.get("status", "").lower() == "finished" else '</span>')}</td>
                </tr>"""
            for r in team_rows
        )
        latest_html = f"""          <div class="table-wrap card">
            <table class="table">
              <thead>
                <tr><th>Driver</th><th class="num">Grid</th><th class="num">Finish</th><th>Result</th></tr>
              </thead>
              <tbody>
{body}
              </tbody>
            </table>
          </div>
          <p class="section__sub">{e(results.get("raceName", ""))} &middot; {e(results.get("date", ""))}</p>"""
    else:
        latest_html = '<p class="state">No race result available yet.</p>'

    # Season wins by any of the team's drivers.
    driver_names = {full_name(d.get("driver", {})) for d in team_drivers}
    wins_list = [r for r in schedule.get("races", []) if (r.get("winner") or "") in driver_names]
    if wins_list:
        items = "\n".join(
            f'              <li>Round {e(r.get("round"))} &mdash; {e(r.get("raceName"))} '
            f'<span class="code">{e(r.get("winner"))}</span></li>'
            for r in wins_list
        )
        wins_html = f"""          <ul class="win-list">
{items}
          </ul>"""
    else:
        wins_html = '<p class="state">No wins yet this season.</p>'

    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "SportsTeam",
            "name": team,
            "sport": "Formula 1",
            "url": BASE_URL + canonical_path,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE_URL},
                {"@type": "ListItem", "position": 2, "name": "Teams",
                 "item": BASE_URL + "index.html#standings"},
                {"@type": "ListItem", "position": 3, "name": team,
                 "item": BASE_URL + canonical_path},
            ],
        },
    ]

    page = f"""{render_head(title, description, canonical_path, '../', json_ld)}
<body class="subpage">
  <a class="skip-link" href="#main">Skip to content</a>
{render_header('../')}

  <main class="container" id="main">
    <section class="section">
{render_breadcrumb('../', 'Teams', '../index.html#standings', team)}

      <header class="profile" style="--team:{color}">
        <div class="profile__id">
          <span class="profile__chip" style="background:{color}" aria-hidden="true"></span>
          <h1 class="profile__name">{e(team)}</h1>
        </div>
        <p class="profile__meta">Constructor{f' &middot; {e(nationality)}' if nationality else ''}</p>
      </header>

      <div class="stats">
        <div class="stat"><span class="stat__label">Championship</span><span class="stat__value">P{e(position)}</span></div>
        <div class="stat"><span class="stat__label">Points</span><span class="stat__value">{e(points)}</span></div>
        <div class="stat"><span class="stat__label">Wins</span><span class="stat__value">{e(wins)}</span></div>
      </div>

      <div class="section__head"><h2 class="section__title">Drivers</h2></div>
      <ul class="win-list">
{driver_links}
      </ul>

      <div class="section__head"><h2 class="section__title">Latest Race Result</h2></div>
{latest_html}

      <div class="section__head"><h2 class="section__title">{season} Wins</h2></div>
{wins_html}
    </section>
  </main>

{render_footer('../')}
"""
    return slug, page


# --------------------------------------------------------------------------- #
# Sitemap
# --------------------------------------------------------------------------- #

def build_sitemap(urls, lastmod):
    entries = []
    for path, priority, changefreq in urls:
        loc = BASE_URL + path if path else BASE_URL
        entries.append(
            "  <url>\n"
            f"    <loc>{e(loc)}</loc>\n"
            f"    <lastmod>{e(lastmod)}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    standings = load_json("standings.json")
    results = load_json("results.json")
    schedule = load_json("schedule.json")
    season = standings.get("season", "2026")

    # Optional season-long archive of per-race results (one results.json-shaped
    # object per completed round). Hermes appends each race here. If it's missing
    # the driver "Results" table falls back to a friendly placeholder.
    try:
        season_results = load_json("season_results.json")
    except FileNotFoundError:
        season_results = {"races": []}

    os.makedirs(DRIVERS_DIR, exist_ok=True)
    os.makedirs(TEAMS_DIR, exist_ok=True)

    # Determine lastmod from the standings 'updated' field (fallback: today).
    lastmod = date.today().isoformat()
    updated = standings.get("updated")
    if updated:
        try:
            lastmod = datetime.fromisoformat(updated.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass

    sitemap_urls = [("", "1.0", "daily")]
    for page in STATIC_PAGES:
        sitemap_urls.append((page, "0.7", "monthly"))

    # Drivers
    driver_count = 0
    for entry in standings.get("driverStandings", []):
        slug, html_out = build_driver_page(entry, season, results, schedule, season_results)
        with open(os.path.join(DRIVERS_DIR, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        sitemap_urls.append((f"drivers/{slug}.html", "0.8", "weekly"))
        driver_count += 1

    # Teams
    team_count = 0
    for entry in standings.get("constructorStandings", []):
        slug, html_out = build_team_page(entry, season, standings, results, schedule)
        with open(os.path.join(TEAMS_DIR, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(html_out)
        sitemap_urls.append((f"teams/{slug}.html", "0.8", "weekly"))
        team_count += 1

    # Sitemap
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_sitemap(sitemap_urls, lastmod))

    print(f"Generated {driver_count} driver pages, {team_count} team pages.")
    print(f"Sitemap: {len(sitemap_urls)} URLs (lastmod {lastmod}).")


if __name__ == "__main__":
    main()
