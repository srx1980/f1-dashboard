# F1 Dashboard

A clean, minimal, English-language Formula 1 dashboard. A single static page that gives F1 fans a quick overview of the current season — the upcoming race, championship standings, latest results, and the full calendar. No frameworks, no build step, no backend.

## Sections

1. **Hero / Header** — title, season year, anchor nav, last-updated timestamp.
2. **Upcoming Race** — circuit details, live countdown, weekend schedule (Qualifying + Race in UTC).
3. **Season Standings** — driver and constructor tables side-by-side.
4. **Latest Race Results** — full results with winner highlight, DNF styling, grid deltas, fastest lap.
5. **Season Calendar** — all races with completed/next highlighting and winners.
6. **Race Summary** *(optional)* — renders `data/summary.md` if present; hidden otherwise.

## How it works — Hermes AI Agent

The site is split into two layers:

| Layer | Owner | Role |
| --- | --- | --- |
| **Frontend** | This repo (HTML/CSS/JS) | Static dashboard that reads JSON and renders the UI |
| **Data** | **Hermes** (AI agent) | Fetches F1 data, writes `/data/*.json` and optional `summary.md`, pushes to Git |
| **Hosting** | GitHub Pages | Serves the repo as static files |

Hermes updates the data files after races and on schedule. The frontend loads them with `fetch({ cache: 'no-cache' })`, so new data appears on the next page load. Hermes does not modify the frontend unless explicitly asked.

## Architecture

```
/index.html        ← the page
/css/style.css     ← styles (dark F1 theme, mobile-first)
/js/main.js        ← fetches /data/*.json and renders everything
/data/*.json       ← written by Hermes (not the frontend)
```

No data is hardcoded in the frontend.

### Data files (provided by Hermes)

| File | Purpose |
| --- | --- |
| `data/standings.json` | Driver + constructor championship standings |
| `data/schedule.json` | Full season calendar (UI shows Qualifying + Race only) |
| `data/results.json` | Latest completed race results |
| `data/summary.md` | *(optional)* AI-generated race summary |

The JSON files committed in this repo are **sample data** for development; Hermes overwrites them in production.

## UI highlights

- **Minimal layout** — driver name + 3-letter code; plain position numbers (no flag or medal emojis)
- **UTC schedule** — Qualifying and Race times in UTC for a global audience
- **Live countdown** — to the next race start, with "LIGHTS OUT 🏁" at T-0
- **Team colors** — accent borders and points bars per constructor
- **Race winner** — gold row highlight and 🏆 in the Time column
- **Dark F1 theme** — mobile-first, responsive, zero external dependencies

## Run locally

Because the page uses `fetch()`, open it through a local server (not `file://`):

```bash
python -m http.server 8000
```

Then visit <http://localhost:8000>.

## Deploy

Works as-is on **GitHub Pages** (or any static host). Push the repo, enable Pages on the default branch, and it serves directly. Add a `CNAME` file with your custom domain if you have one.

When you change frontend CSS/JS, bump the `?v=N` query string on the asset links in `index.html` so browsers pick up the new files.

## Configuration

- **Analytics:** replace `YOUR_CODE` in the GoatCounter snippet at the bottom of `index.html` (or remove the snippet).
- **Assets:** add `assets/favicon.ico` and `assets/og-image.png` for favicon and social previews.

## Constraints

Vanilla HTML/CSS/JS only — no frameworks, no bundlers, no external runtime dependencies. Dark theme, mobile-first, single scrollable page.

## Agent instructions

See [`CLAUDE.md`](CLAUDE.md) for full build specs, JSON schemas, and Cursor agent guidelines.
