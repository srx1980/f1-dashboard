/* ===========================================================================
   F1 Dashboard — main.js
   Vanilla JS. Fetches /data/*.json, renders the dashboard, runs a live
   countdown, and displays session times in UTC for a global audience.
   Zero external dependencies.
   =========================================================================== */

'use strict';

const DATA = {
  standings: 'data/standings.json',
  schedule: 'data/schedule.json',
  results: 'data/results.json',
};

/* ----------------------------------------------------------- Utilities --- */

const $ = (sel, root = document) => root.querySelector(sel);

/** Escape user-facing strings before injecting into innerHTML. */
function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function getJSON(url) {
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
  return res.json();
}

/** Combine an Ergast-style { date, time } pair into a Date (UTC). */
function toDate(date, time) {
  if (!date) return null;
  const t = time || '00:00:00Z';
  const iso = `${date}T${t.endsWith('Z') || t.includes('+') ? t : t + 'Z'}`;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

/** English date/time in UTC — same for every viewer worldwide. */
const fmtUTC = (d) =>
  d ? `${d.toLocaleString('en-GB', {
    timeZone: 'UTC',
    weekday: 'long', day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
    hour12: false,
  })} UTC` : 'TBD';

const fmtDate = (d) =>
  d ? d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : 'TBD';

/** Relative "updated X ago" string. */
function relativeTime(d) {
  if (!d) return 'unknown';
  const diff = Date.now() - d.getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs > 1 ? 's' : ''} ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

const num = (v) => { const n = parseFloat(v); return isNaN(n) ? 0 : n; };

/* ----------------------------------------------------- Team color chips --- */

const TEAM_COLORS = {
  Mercedes: '#27f4d2', Ferrari: '#e8002d', McLaren: '#ff8000',
  'Red Bull Racing': '#3671c6', Alpine: '#0093cc', 'Racing Bulls': '#6692ff',
  'Haas F1 Team': '#b6babd', Williams: '#64c4ff', Audi: '#00a19b',
  'Aston Martin': '#229971', Cadillac: '#c69a4e',
  // Legacy / alternate names kept for backwards compatibility
  'Red Bull': '#3671c6', RB: '#6692ff', Sauber: '#52e252', Haas: '#b6babd',
};
const teamColor = (t) => TEAM_COLORS[t] || '#888';

/* --------------------------------------------------- Internal page links --- */
/* Slug rules must match scripts/generate_pages.py (slugify / driver code). */

const teamSlug = (name) =>
  String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

/** Link a driver name cell to its page, if a 3-letter code is available. */
function driverLink(code, inner) {
  const c = String(code || '').trim().toLowerCase();
  if (!c) return inner;
  return `<a class="entity-link" href="drivers/${c}.html">${inner}</a>`;
}

/** Link a team/constructor cell to its page. */
function teamLink(name, inner) {
  const slug = teamSlug(name);
  if (!slug) return inner;
  return `<a class="entity-link" href="teams/${slug}.html">${inner}</a>`;
}

/* --------------------------------------------------------- Error helper --- */

function showError(tbodyId, cols, msg) {
  const el = document.getElementById(tbodyId);
  if (el) el.innerHTML = `<tr><td colspan="${cols}" class="state state--error">${esc(msg)}</td></tr>`;
}

/* --------------------------------------------------- Skeleton loaders --- */

/** Fill a table body with shimmering placeholder rows while data loads. */
function skeletonRows(tbodyId, rows, cols) {
  const el = document.getElementById(tbodyId);
  if (!el) return;
  let html = '';
  for (let i = 0; i < rows; i++) {
    let cells = '<td class="col-pos"><span class="skeleton skeleton--pos"></span></td>';
    for (let c = 1; c < cols; c++) {
      const w = 40 + ((i * 11 + c * 17) % 45); // pseudo-varied 40–85%
      cells += `<td><span class="skeleton" style="width:${w}%"></span></td>`;
    }
    html += `<tr class="skeleton-row" aria-hidden="true">${cells}</tr>`;
  }
  el.innerHTML = html;
}

/** Placeholder banner + schedule for the upcoming race. */
function skeletonUpcoming() {
  const el = $('#upcoming-content');
  if (!el) return;
  el.innerHTML = `
    <div class="race-banner" aria-hidden="true">
      <span class="skeleton" style="width:80px;height:0.7em"></span>
      <span class="skeleton skeleton--title"></span>
      <span class="skeleton" style="width:42%;height:0.85em"></span>
      <div class="countdown countdown--big">
        <div class="cd-unit"><span class="skeleton skeleton--num"></span></div>
        <div class="cd-unit"><span class="skeleton skeleton--num"></span></div>
        <div class="cd-unit"><span class="skeleton skeleton--num"></span></div>
        <div class="cd-unit"><span class="skeleton skeleton--num"></span></div>
      </div>
    </div>
    <div class="schedule" aria-hidden="true">
      <div class="schedule__row"><span class="skeleton" style="width:30%;height:0.8em"></span><span class="skeleton" style="width:35%;height:0.8em"></span></div>
      <div class="schedule__row"><span class="skeleton" style="width:25%;height:0.8em"></span><span class="skeleton" style="width:40%;height:0.8em"></span></div>
    </div>`;
}

/** Show all loading placeholders at once, before the first fetch resolves. */
function showSkeletons() {
  const u = $('#updated-text');
  if (u) u.innerHTML = '<span class="skeleton" style="width:130px;height:0.7em"></span>';
  skeletonUpcoming();
  skeletonRows('driver-standings-body', 8, 5);
  skeletonRows('constructor-standings-body', 6, 4);
  skeletonRows('results-body', 10, 6);
  skeletonRows('calendar-body', 8, 5);
}

/* ===========================================================================
   Renderers
   =========================================================================== */

function renderStandings(data) {
  if (data.season) $('#hero-season').textContent = `${data.season} Season`;

  const updatedDate = data.updated ? new Date(data.updated) : null;
  $('#updated-text').textContent = updatedDate
    ? `Updated ${relativeTime(updatedDate)} · Round ${esc(data.round)}`
    : 'Live data';

  const sub = `Last updated: Round ${esc(data.round)}`;
  $('#standings-sub').textContent = sub;

  const posCell = (position) => `<span class="pos">${esc(position)}</span>`;
  const ptsCell = (points, max, color) => {
    const pct = max > 0 ? Math.max(3, Math.round((num(points) / max) * 100)) : 0;
    return `<div class="pts">
        <strong>${esc(points)}</strong>
        <span class="pts-bar"><span class="pts-bar__fill" style="width:${pct}%;background:${color}"></span></span>
      </div>`;
  };

  // Drivers
  const dBody = $('#driver-standings-body');
  const drivers = data.driverStandings || [];
  if (!drivers.length) {
    showError('driver-standings-body', 5, 'No driver standings available.');
  } else {
    const maxPts = Math.max(...drivers.map((d) => num(d.points)), 0);

    dBody.innerHTML = drivers.map((d) => {
      const drv = d.driver || {};
      const color = teamColor(d.constructor);
      return `
        <tr style="--team:${color}">
          <td class="col-pos">${posCell(d.position)}</td>
          <td>
            ${driverLink(drv.code, `<span class="driver">
              <span class="driver__name">${esc(drv.givenName)} ${esc(drv.familyName)}</span>
              <span class="code">${esc(drv.code)}</span>
            </span>`)}
          </td>
          <td><span class="team"><span class="team__chip" style="background:${color}"></span>${teamLink(d.constructor, esc(d.constructor))}</span></td>
          <td class="num">${ptsCell(d.points, maxPts, color)}</td>
          <td class="num">${esc(d.wins)}</td>
        </tr>`;
    }).join('');
  }

  // Constructors
  const cBody = $('#constructor-standings-body');
  const teams = data.constructorStandings || [];
  if (!teams.length) {
    showError('constructor-standings-body', 4, 'No constructor standings available.');
  } else {
    const maxPts = Math.max(...teams.map((t) => num(t.points)), 0);
    cBody.innerHTML = teams.map((t) => {
      const color = teamColor(t.constructor);
      return `
        <tr style="--team:${color}">
          <td class="col-pos">${posCell(t.position)}</td>
          <td><span class="team"><span class="team__chip" style="background:${color}"></span>${teamLink(t.constructor, `<strong>${esc(t.constructor)}</strong>`)}</span></td>
          <td class="num">${ptsCell(t.points, maxPts, color)}</td>
          <td class="num">${esc(t.wins)}</td>
        </tr>`;
    }).join('');
  }
}

function renderResults(data) {
  const loc = data.circuit?.location;
  const where = loc ? ` · ${loc.locality}, ${loc.country}` : '';
  const raceDate = toDate(data.date, null);
  $('#results-sub').textContent =
    `${data.raceName || ''} · ${data.circuit?.circuitName || ''}${where} · ${fmtDate(raceDate)}`;

  const body = $('#results-body');
  const rows = data.results || [];
  if (!rows.length) { showError('results-body', 6, 'No results available yet.'); return; }

  body.innerHTML = rows.map((r) => {
    const finished = (r.status || '').toLowerCase() === 'finished';
    const isDnf = !finished && r.position === 'R';
    const drv = r.driver || {};
    const color = teamColor(r.constructor);
    const pos = parseInt(r.position, 10);

    const classes = [];
    if (r.position === '1') classes.push('row--winner');
    if (isDnf) classes.push('row--dnf');

    let posCell;
    if (isDnf) {
      posCell = `<span class="pos pos--dnf">DNF</span>`;
    } else {
      posCell = `<span class="pos">${esc(r.position)}</span>`;
    }

    let timeCell;
    if (finished) {
      const trophy = r.position === '1' ? '<span class="trophy" aria-hidden="true">🏆</span> ' : '';
      timeCell = `${trophy}<span class="gap">${esc(r.time || '—')}</span>`;
    } else {
      timeCell = `<span class="status--dnf">${esc(r.status)}</span>`;
    }

    // Grid → finish position change
    const grid = parseInt(r.grid, 10);
    let gridCell = `<span class="grid-num">${esc(r.grid)}</span>`;
    if (!isNaN(grid) && !isNaN(pos)) {
      const delta = grid - pos; // positive = places gained
      if (delta > 0) gridCell += ` <span class="delta delta--up" title="Gained ${delta}">▲${delta}</span>`;
      else if (delta < 0) gridCell += ` <span class="delta delta--down" title="Lost ${-delta}">▼${-delta}</span>`;
      else gridCell += ` <span class="delta delta--same" title="No change">▬</span>`;
    }

    const fl = r.fastestLap;
    const flCell = fl
      ? `<span class="${fl.rank === '1' ? 'fl-purple' : ''}">${esc(fl.time)}${fl.rank === '1' ? ' ⏱' : ''}</span>`
      : '<span class="tbd">—</span>';

    return `
      <tr class="${classes.join(' ')}" style="--team:${color}">
        <td class="col-pos">${posCell}</td>
        <td>
          ${driverLink(drv.code, `<span class="driver">
            <span class="driver__name">${esc(drv.givenName)} ${esc(drv.familyName)}</span>
            <span class="code">${esc(drv.code)}</span>
          </span>`)}
        </td>
        <td><span class="team"><span class="team__chip" style="background:${color}"></span>${teamLink(r.constructor, esc(r.constructor))}</span></td>
        <td>${timeCell}</td>
        <td class="num">${gridCell}</td>
        <td>${flCell}</td>
      </tr>`;
  }).join('');
}

function renderCalendar(schedule) {
  const races = schedule.races || [];
  $('#calendar-sub').textContent = `${races.length} races`;

  const now = Date.now();
  // The "next" race is the first one in the future without a winner.
  let nextRound = null;
  for (const r of races) {
    const d = toDate(r.date, r.time);
    if (!r.winner && d && d.getTime() > now) { nextRound = r.round; break; }
  }

  const body = $('#calendar-body');
  if (!races.length) { showError('calendar-body', 5, 'No calendar available.'); return; }

  body.innerHTML = races.map((r) => {
    const d = toDate(r.date, r.time);
    const done = !!r.winner;
    const isNext = r.round === nextRound;

    const cls = [];
    if (done) cls.push('row--done');
    if (isNext) cls.push('row--next');

    const winnerCell = r.winner
      ? `<span class="check" aria-hidden="true">✓</span>${esc(r.winner)}`
      : (isNext
          ? `<span class="tbd">Up next</span><span class="next-tag">Next</span>`
          : `<span class="tbd">TBD</span>`);

    return `
      <tr class="${cls.join(' ')}">
        <td class="col-pos"><span class="cal-round">${esc(r.round)}</span></td>
        <td>${fmtDate(d)}</td>
        <td>${esc(r.raceName)}</td>
        <td><span class="team">${esc(r.circuit?.circuitName)}</span></td>
        <td>${winnerCell}</td>
      </tr>`;
  }).join('');
}

/* -------------------------------------------------------- Upcoming race --- */

let countdownTimer = null;

function renderUpcoming(schedule) {
  const races = schedule.races || [];
  const now = Date.now();

  const next = races.find((r) => {
    const d = toDate(r.date, r.time);
    return d && d.getTime() > now;
  });

  const el = $('#upcoming-content');
  if (!next) {
    el.innerHTML = `<p class="state">The 2026 season is complete. See you next year! 🏁</p>`;
    return;
  }

  const raceDate = toDate(next.date, next.time);
  const loc = next.circuit?.location;
  const hasSprint = !!(next.sprint || next.sprintQualifying);

  const sessions = [
    ['Qualifying', next.qualifying],
    ['Race', { date: next.date, time: next.time }],
  ].filter(([, s]) => s && s.date);

  const scheduleRows = sessions.map(([label, s]) => {
    const d = toDate(s.date, s.time);
    const isRace = label === 'Race';
    return `
      <div class="schedule__row${isRace ? ' is-race' : ''}">
        <span class="schedule__label">${esc(label)}</span>
        <span class="schedule__when">${fmtUTC(d)}</span>
      </div>`;
  }).join('');

  el.innerHTML = `
    <div class="race-banner">
      <div class="race-banner__head">
        <span class="race-card__round">Round ${esc(next.round)}${hasSprint ? '<span class="badge-sprint">Sprint</span>' : ''}</span>
        <h3 class="race-banner__name">${esc(next.raceName)}</h3>
        <p class="race-card__circuit">
          ${esc(next.circuit?.circuitName)}
          — ${esc(loc?.locality)}, ${esc(loc?.country)}
        </p>
      </div>

      <div class="countdown countdown--big" id="countdown" role="timer" aria-live="off">
        <div class="cd-unit"><span class="cd-num" id="cd-d">--</span><span class="cd-label">Days</span></div>
        <span class="cd-sep" aria-hidden="true">:</span>
        <div class="cd-unit"><span class="cd-num" id="cd-h">--</span><span class="cd-label">Hours</span></div>
        <span class="cd-sep" aria-hidden="true">:</span>
        <div class="cd-unit"><span class="cd-num" id="cd-m">--</span><span class="cd-label">Mins</span></div>
        <span class="cd-sep" aria-hidden="true">:</span>
        <div class="cd-unit"><span class="cd-num" id="cd-s">--</span><span class="cd-label">Secs</span></div>
      </div>

      <p class="countdown__caption" id="cd-caption">
        until lights out · <strong>${fmtUTC(raceDate)}</strong>
      </p>
    </div>

    <div class="schedule" aria-label="Weekend schedule (UTC)">
      <div class="schedule__title">Weekend Schedule <span>· UTC</span></div>
      ${scheduleRows}
    </div>`;

  startCountdown(raceDate);
}

function startCountdown(target) {
  if (countdownTimer) clearInterval(countdownTimer);
  if (!target) return;

  const cdEl = $('#countdown');
  const dEl = $('#cd-d'), hEl = $('#cd-h'), mEl = $('#cd-m'), sEl = $('#cd-s');
  const pad = (n) => String(n).padStart(2, '0');

  const tick = () => {
    const diff = target.getTime() - Date.now();
    if (diff <= 0) {
      clearInterval(countdownTimer);
      if (cdEl) {
        cdEl.classList.add('countdown--live');
        cdEl.innerHTML = `<div class="cd-live">LIGHTS OUT <span aria-hidden="true">🏁</span></div>`;
      }
      const cap = document.getElementById('cd-caption');
      if (cap) cap.innerHTML = '<strong>Race in progress</strong>';
      return;
    }
    const days = Math.floor(diff / 86400000);
    const hrs = Math.floor((diff % 86400000) / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    if (dEl) dEl.textContent = days;
    if (hEl) hEl.textContent = pad(hrs);
    if (mEl) mEl.textContent = pad(mins);
    if (sEl) sEl.textContent = pad(secs);
  };

  tick();
  countdownTimer = setInterval(tick, 1000);
}

/* --------------------------------------------------------- Smooth nav --- */

function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (id.length < 2) return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', id);
    });
  });
}

/* ----------------------------------------------- Reveal on scroll --- */

function initReveal() {
  const sections = document.querySelectorAll('.section');
  if (!('IntersectionObserver' in window) ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    sections.forEach((s) => s.classList.add('is-visible'));
    return;
  }
  const io = new IntersectionObserver((entries, obs) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('is-visible'); obs.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.06 });
  sections.forEach((s) => { s.classList.add('reveal'); io.observe(s); });
}

/* ===========================================================================
   Boot
   =========================================================================== */

async function init() {
  initSmoothScroll();
  initReveal();
  showSkeletons();

  const [standingsRes, scheduleRes, resultsRes] = await Promise.allSettled([
    getJSON(DATA.standings),
    getJSON(DATA.schedule),
    getJSON(DATA.results),
  ]);

  let schedule = null;
  let results = null;

  if (standingsRes.status === 'fulfilled') {
    try { renderStandings(standingsRes.value); }
    catch (e) { console.error(e); showError('driver-standings-body', 5, 'Failed to render standings.'); }
  } else {
    console.error(standingsRes.reason);
    $('#updated-text').textContent = 'Data unavailable';
    showError('driver-standings-body', 5, 'Could not load standings.');
    showError('constructor-standings-body', 4, 'Could not load standings.');
  }

  if (scheduleRes.status === 'fulfilled') {
    schedule = scheduleRes.value;
    try {
      renderUpcoming(schedule);
    } catch (e) { console.error(e); $('#upcoming-content').innerHTML = '<p class="state state--error">Failed to render upcoming race.</p>'; }
  } else {
    console.error(scheduleRes.reason);
    $('#upcoming-content').innerHTML = '<p class="state state--error">Could not load the race schedule.</p>';
    showError('calendar-body', 5, 'Could not load the calendar.');
  }

  if (resultsRes.status === 'fulfilled') {
    results = resultsRes.value;
    try { renderResults(results); }
    catch (e) { console.error(e); showError('results-body', 6, 'Failed to render results.'); }
  } else {
    console.error(resultsRes.reason);
    showError('results-body', 6, 'Could not load the latest results.');
  }

  if (schedule) {
    try { renderCalendar(schedule); }
    catch (e) { console.error(e); showError('calendar-body', 5, 'Failed to render calendar.'); }
  }

  // Summary is now static HTML in index.html (for SEO). No JS fetch needed.
}

document.addEventListener('DOMContentLoaded', init);
