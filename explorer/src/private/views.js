/* The private build's overlays: the Needs you group and the panels each
   shared group adds from the dashboard's own datasets. Every panel hides
   itself when its datasets are empty, so a dashboard with only the explorer
   dataset shows the public views alone. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDateTime, fmtDay, fmtCount, fmtUsd, fmtWeekStart, fmtResetLabel, utcClockToEt, utcMomentToEt } from '../core/format.js';
import { h } from '../core/h.js';
import { hashFor } from '../core/route.js';
import { table, panel, fold, srcLine, tile, badge, navLink, foldSummary } from '../views/bits.js';
import { alertText, alertHref } from '../views/alerts.js';
import { problemsToggle, PROBLEMS_PANEL, runName } from '../views/ops.js';
import { rowsOf, some } from './datasets.js';
import { P } from './strings.js';
import { conversionView } from './conversion.js';
import { isTrending, alertKindLabel } from '../core/stats.js';
import { LOOP_BRANCH, LIST_CAP, repoNumber } from '../views/loop.js';

const at = (s) => (s ? fmtDateTime(parseTime(s)) : STRINGS.noValue);
const n = (v) => (v === null || v === undefined ? '' : fmtCount(v));
const usd = (v) => (typeof v === 'number' ? fmtUsd(v) : STRINGS.noValue);
const SAFE = /^https:\/\/(github\.com|claude\.ai)\//;
export function plink(url, text) {
  return typeof url === 'string' && SAFE.test(url) ? h('a', { href: url, rel: 'noopener', target: '_blank' }, text) : text;
}
/* plink, plus a '#/' route as a link to a page here. */
const ROUTE = /^#\/[a-z]/;
export function rowLink(url, text) {
  return typeof url === 'string' && ROUTE.test(url) ? navLink(url, text) : plink(url, text);
}
function pill(text) {
  const t = String(text || '');
  const kind = /^(Done|OK|Met|Succeeded|Passed|ok|clear)$/i.test(t) ? 'good'
    : /stalled|stopped|not started|failed|^(high|broken)$/i.test(t) ? 'bad'
      : /waiting|partly|needs|not yet|in progress|^(Running|Queued|medium)$/i.test(t) ? 'warn' : '';
  return h('span', { class: 'st ' + kind }, clean(t));
}
const src = (id) => P.srcSnapshot(id);
const isLoopBranch = (b) => LOOP_BRANCH.test(String(b || ''));

/* "Monday noon ET": the weekday and clock time of a reset, in US Eastern,
   read from the reset itself rather than assumed. */
export function resetLabel(iso) {
  return fmtResetLabel(parseTime(iso));
}

/* Who opened a pull request, in a few words beside its title: "by a bot" or "by <login>".
   GitHub's own account type says so (`Bot`); a login ending in [bot] is the fallback. */
export function byLine(author, type) {
  const a = String(author || '').trim();
  if (!a) return '';
  return type === 'Bot' || /\[bot\]$/i.test(a) ? 'by a bot' : 'by ' + clean(a);
}

const WEEKDAY_STEMS = ['Mon', 'Tues', 'Wednes', 'Thurs', 'Fri', 'Satur', 'Sun'];
const WEEKDAY_WORD = /\b(?:Mon|Tues?|Wed(?:nes)?|Thu(?:rs?)?|Fri|Sat(?:ur)?|Sun)(?:days?|s)?\b/i;
const MONTH_WORD = /\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b|\b\d{4}-\d{2}-\d{2}\b/i;
/* "Mondays 02:00 UTC", "Nov 2 at 16:57 UTC", "at 07:00 UTC" or a bare "07:00 UTC". */
const BARE_UTC = /(?:\b((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)days?)\s+|\b(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)) (\d{1,2}) at\s+|\bat\s+)?\b(\d{1,2}):(\d{2}) UTC\b/gi;
/* A UTC clock time that already has its Eastern time beside it: "06:53 UTC, GitHub Actions (1:53 AM ET)". */
const UTC_WITH_ET = /(?:\b((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)days?)\s+)?(\d{1,2}):(\d{2}) UTC([^()]*)\(([^()]*\bET)\)/gi;
/* The text of the clause before a match: since the last ; . or ( . */
const clauseBefore = (whole, offset) => whole.slice(0, offset).split(/[;.(]/).pop();

/* The weekday one day earlier, keeping the word's shape: Mondays to Sundays, TUESDAY to MONDAY. */
function prevWeekday(word) {
  const m = /^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)(days?)$/i.exec(word);
  const i = WEEKDAY_STEMS.findIndex((x) => x.toLowerCase() === m[1].toLowerCase());
  const out = WEEKDAY_STEMS[(i + 6) % 7] + m[2].toLowerCase();
  return word === word.toLowerCase() ? out.toLowerCase() : word === word.toUpperCase() ? out.toUpperCase() : out;
}

/* A routine's schedule or note in US Eastern only. The routine list words some
   schedules as "Daily 06:53 UTC, GitHub Actions (1:53 AM ET)": the Eastern time
   in the parentheses replaces the UTC one, and a "UTC hours ..." aside keeps
   only its Eastern list. A bare UTC time is converted, and a weekday word before
   it moves back a day when Eastern time is the evening before. A dated one
   ("Oct 30 at 16:57 UTC") is converted at its own moment. Anything else that
   names a weekday or date it cannot move is left as the data wrote it. */
export function etSchedule(text, refMs) {
  return String(text === null || text === undefined ? '' : text)
    .replace(UTC_WITH_ET, (m, wd, hh, mm, mid, et, offset, whole) => {
      const { shift } = utcClockToEt(hh, mm, refMs);
      const before = clauseBefore(whole, offset);
      if (shift !== 0 && WEEKDAY_WORD.test(before)) return m;
      const rest = mid.trim();
      return (wd ? (shift !== 0 ? prevWeekday(wd) : wd) + ' ' : '') + et + (rest ? (rest.startsWith(',') ? rest : ' ' + rest) : '');
    })
    .replace(/\(UTC hours [^:()]*: /g, '(')
    .replace(BARE_UTC, (m, wd, mon, day, hh, mm, offset, whole) => {
      const before = clauseBefore(whole, offset);
      if (mon) {
        const r = utcMomentToEt(mon, day, hh, mm, refMs);
        if (!r) return m;
        if (r.date !== r.named && WEEKDAY_WORD.test(before)) return m;
        return r.date + ' at ' + r.clock;
      }
      const { text, shift } = utcClockToEt(hh, mm, refMs);
      const at = /^at\s/i.test(m);
      if (shift === 0) return (wd ? wd + ' ' : at ? 'at ' : '') + text;
      if (WEEKDAY_WORD.test(before) || MONTH_WORD.test(before)) return m;
      return wd ? prevWeekday(wd) + ' ' + text : (at ? 'at ' : '') + text;
    });
}

/* Test use this week against the cap, from eval_allowance and budget. */
export function capUse(allowance, budget) {
  const a = (allowance && allowance[0]) || null;
  if (!a || !budget) return null;
  const b = {};
  budget.forEach((r) => { b[r.setting] = r.value; });
  const cap = (Number(b.weekly_cap) || 0) * 100;
  const left = Math.max(0, cap - (Number(a.points) || 0));
  return { spent: Number(a.points) || 0, cap, stop: (Number(b.stop_when_account_above) || 0) * 100, accountUsed: a.account_week_used,
    /* The guard's own room when the row carries it, else re-derived. */
    room: typeof a.room_points === 'number' ? Math.max(0, a.room_points) : Math.max(left, Number(a.pace_room_points) || 0), reservation: ((Number(b.per_run_cap) || 0) + (Number(b.per_run_overrun) || 0)) * 100,
    readingAt: a.account_reading_at, resetsAt: a.week_resets_at,
    /* The window's own start when the row has it (a manual reset can fall mid-week), else the week's reset. */
    resetLabel: resetLabel(a.window_start || a.week_resets_at),
    /* eval_spend_7d is a rolling window; anything naming the reset is counted since it. */
    basis: a.measure === 'eval_spend_7d' ? 'rolling' : /since_reset|reset/.test(String(a.measure || '')) ? 'reset' : 'plain' };
}

/* Every routine is counted once: healthy, not run yet, or needing a look, so
   the three add up to `active`, the rows the table lists (build.py leaves
   retired routines out of the dataset). */
export function routineHealth(routines) {
  if (!routines) return null;
  const ok = routines.filter((r) => r.health === 'OK').length;
  const fresh = routines.filter((r) => r.health === 'Not run yet').length;
  return { active: routines.length, ok, fresh, attention: routines.length - ok - fresh };
}

function meter(value, max, mark, over) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return h('div', { class: 'meter' }, h('div', { class: 'fill' + ((over === undefined ? value > max : over) ? ' over' : ''), style: 'width:' + pct.toFixed(1) + '%' }),
    mark !== undefined ? h('div', { class: 'meter-mark', style: 'left:' + Math.min(100, mark).toFixed(1) + '%' }) : null);
}

/* An alert's line: its text, led by its name unless the text already
   starts with it ("tool-powershell: tool-powershell regressed ..."). */
export function alertWhat(a) {
  const name = clean(a.name);
  const text = a.text ? clean(a.text) : alertText(a) || '';
  if (!text) return name;
  return text.startsWith(name + ' ') ? text : name + ': ' + text;
}

/* One list of what needs attention, with a kind column. */
export function attentionRows(dash, doc) {
  const rows = [];
  for (const r of some(dash, 'half_built_issues') || []) {
    if (r.state !== 'open') continue;
    rows.push({ kind: P.kindHalfBuilt(r.kind), severity: r.severity, what: r.title, url: r.url, where: r.repo, age: r.age_days, acts: P.actsHalfBuilt, family: 'half-built', hbKind: r.kind });
  }
  for (const a of Array.isArray(doc.alerts) ? doc.alerts : []) {
    if (!a) continue;
    // A regression on an undecided subject is trending toward removal, not an
    // item that needs attention: its own table. On a decided one it is listed.
    if (isTrending(doc, a)) continue;
    const k = alertKindLabel(doc, a);
    rows.push({ kind: P.kindAlert(k), severity: 'medium', what: alertWhat(a), url: alertHref(a), where: a.subject, age: null, name: a.name, alertKind: a.kind, since: a.drift_since, acts: P.actsAlert, family: 'alert', subject: a.subject });
  }
  const f = doc.fires_without_results;
  if (f && Number.isInteger(f.without_results) && (f.without_results || f.rejected) && typeof f.since === 'string') {
    rows.push({ kind: P.kindFires, severity: 'medium', what: STRINGS.firesLine(f.without_results, Number.isInteger(f.counted) ? f.counted : null, at(f.since), Array.isArray(f.sweeps) ? f.sweeps.length : 0, f.rejected || 0), url: hashFor('activity'), where: null, age: null });
  }
  const q = doc.fixture_queue;
  for (const x of q && Array.isArray(q.findings) ? q.findings : []) {
    if (x) rows.push({ kind: P.kindFixture(x.kind || ''), severity: x.severity || 'unknown', what: clean(x.subject || x.finding_id || ''), url: x.url, where: null, age: null, acts: P.actsFixture(x.kind || ''), family: 'fixture' });
  }
  const order = { high: 0, medium: 1, low: 2 };
  return rows.sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
}

/* The refresh clock the dashboard uploads on every refresh (dashboard/build.py's
   `refresh` dataset): when the snapshot was built and how many hours a refresh
   is due every. The allowance row's own clock is the fallback for a dashboard
   without that dataset; 12 is the fallback interval. */
export const REFRESH_HOURS = 12;
const HOUR_MS = 3600000;
const refreshRow = (dash) => (rowsOf(dash, 'refresh') || [])[0] || null;

export function refreshHours(dash) {
  const r = refreshRow(dash);
  return r && Number.isFinite(r.refresh_every_hours) && r.refresh_every_hours > 0 ? r.refresh_every_hours : REFRESH_HOURS;
}

/* When the newest snapshot was built; NaN when no dataset says. */
export function snapshotMs(dash) {
  const r = refreshRow(dash);
  if (r && isFinite(parseTime(r.refreshed_at))) return parseTime(r.refreshed_at);
  const a = rowsOf(dash, 'eval_allowance');
  return a && a[0] ? parseTime(a[0].computed_at) : NaN;
}

/* Whole hours the snapshot is old when that is more than an hour past a
   refresh interval, else null. */
export function staleHours(snapMs, nowMs, every) {
  if (!isFinite(snapMs) || !isFinite(nowMs)) return null;
  const hours = (nowMs - snapMs) / HOUR_MS;
  return hours > (every || REFRESH_HOURS) + 1 ? Math.floor(hours) : null;
}

/* "As of <time ET>", the dataset id kept for the hover text. */
function asOfLine(id, ms) {
  return isFinite(ms) ? h('p', { class: 'src', title: id }, P.asOf(fmtDateTime(ms))) : null;
}

/* Rows of one kind fold into a single row once there are more than this. */
export const GROUP_OVER = 3;
const SEVERITY = { high: 0, medium: 1, low: 2 };

/* Where a folded row's title links, so the group is clickable while shut:
   fixture findings to the Changes page's fixture requests, half-built issues
   to an issue search on their label and Kind in the owners their rows name, alerts on
   one kind of subject to that subject's list here. */
const HALF_BUILT_LABEL = 'half-built-or-broken';
export function groupHref(list) {
  const fam = list[0].family;
  if (fam === 'fixture') return hashFor('changes');
  if (fam === 'half-built') {
    const owners = [...new Set(list.map((r) => String(r.where || '').split('/')[0]).filter((o) => /^[A-Za-z0-9-]+$/.test(o)))].sort();
    if (!owners.length) return null;
    // The group is one Kind (a header line in each issue body, not a label).
    const kind = /^[a-z-]+$/.test(String(list[0].hbKind || '')) ? ['"Kind: ' + list[0].hbKind + '"', 'in:body'] : [];
    const q = ['is:issue', 'is:open', 'label:' + HALF_BUILT_LABEL].concat(kind, owners.map((o) => 'user:' + o)).join(' ');
    return 'https://github.com/search?type=issues&q=' + encodeURIComponent(q);
  }
  if (fam === 'alert') {
    const subjects = new Set(list.map((r) => r.subject));
    const one = subjects.size === 1 ? [...subjects][0] : null;
    return one === 'skill' ? hashFor('skills') : one === 'guidance' ? hashFor('guidance') : null;
  }
  return null;
}

/* The Needs you list with a kind that has many rows folded into one row (the
   individual rows stay in `children`), so 29 copies of one notice are one
   line. attentionRows stays the flat list, which the Summary's count reads. */
export function attentionGroups(rows) {
  const by = new Map();
  for (const r of rows) {
    if (!by.has(r.kind)) by.set(r.kind, []);
    by.get(r.kind).push(r);
  }
  const out = [];
  for (const list of by.values()) {
    if (list.length <= GROUP_OVER) { list.forEach((r) => out.push(r)); continue; }
    const drift = list[0].alertKind === 'context-drift';
    const names = new Set(list.map((r) => r.name).filter(Boolean));
    const since = list.map((r) => r.since).filter((x) => typeof x === 'string').sort()[0];
    const worst = list.reduce((a, r) => ((SEVERITY[r.severity] ?? 3) < (SEVERITY[a] ?? 3) ? r.severity : a), list[0].severity);
    out.push({ kind: list[0].kind, severity: worst, what: drift ? P.driftTitle(list.length, names.size) : P.groupTitle(list.length, list[0].kind),
      note: drift ? P.driftNote(since ? fmtDay(parseTime(since)) : STRINGS.unknown) : list[0].acts || null, url: groupHref(list),
      helpUrl: drift ? P.driftHelpUrl : null, where: null, age: null, children: list });
  }
  return out.sort((a, b) => (SEVERITY[a.severity] ?? 3) - (SEVERITY[b.severity] ?? 3));
}

/* A group row's cell: its title, the note on who acts, and every row under a fold. */
function attentionWhat(r) {
  if (!r.children) return rowLink(r.url, clean(r.what));
  return [h('strong', null, rowLink(r.url, clean(r.what))), r.note ? h('p', { class: 'note' }, r.note, r.helpUrl ? [' ', plink(r.helpUrl, P.driftHelpLink)] : null) : null,
    h('details', { class: 'history' }, foldSummary(P.showAll(r.children.length)),
      h('ul', { class: 'plain' }, r.children.map((c) => h('li', null, rowLink(c.url, clean(c.what))))))];
}

/* The use line, its bar and the room line must agree: when the guard still
   has room, a spend above the cap is the rolling window's, not a breach, so
   the bar is scaled to the larger of the two, marked at the cap, and red only
   when there is no room. */
export function allowanceView(cap, snapMs, id) {
  const room = cap.room > 0;
  const scale = Math.max(cap.cap, cap.spent);
  const use = cap.basis === 'rolling' ? P.allowanceUseRolling(cap.spent.toFixed(1), cap.cap.toFixed(0))
    : cap.basis === 'reset' ? P.allowanceUseReset(cap.spent.toFixed(1), cap.cap.toFixed(0), cap.resetLabel) : P.allowanceUsePlain(cap.spent.toFixed(1), cap.cap.toFixed(0));
  return [asOfLine(id || 'eval_allowance', snapMs),
    h('p', null, use),
    meter(cap.spent, scale, scale > 0 ? (cap.cap / scale) * 100 : undefined, cap.spent > cap.cap && !room),
    cap.spent > cap.cap && room ? h('p', { class: 'note' }, P.allowancePace) : null,
    cap.accountUsed !== null && cap.accountUsed !== undefined ? [h('p', null, P.allowanceAccount(Math.round(cap.accountUsed), cap.stop.toFixed(0))), meter(cap.accountUsed, 100, cap.stop)] : null,
    h('p', { class: 'note' }, P.allowanceRoom(cap.room.toFixed(1), cap.reservation.toFixed(1))),
    h('p', { class: 'note' }, P.allowanceReading(at(cap.readingAt), at(cap.resetsAt), cap.resetLabel))];
}

const link = (hash, text) => h('a', { href: hash, class: 'nav-link' }, text);

/* One line on whether the loop is working, each part a link to where it is
   explained. Healthy only when every routine is on time and the snapshot is
   fresh; with no routine data it says so rather than claim health. */
export function healthStrip(doc, rh, stale) {
  const when = (t) => (typeof t === 'string' && isFinite(parseTime(t)) ? at(t) : STRINGS.noValue);
  const routines = rh ? (rh.attention ? P.hsRoutinesBad(rh.attention, rh.active) : P.hsRoutinesOk(rh.ok, rh.active)) : null;
  const state = !rh ? 'unknown' : rh.attention || stale !== null ? 'attention' : 'healthy';
  return [P.hsState[state], ' ', link(hashFor('activity'), P.hsLastTest(when(doc.newest_run))), '; ', routines ? [link(hashFor('activity'), routines), '; '] : null,
    link(hashFor('summary'), P.hsDataRead(when(doc.generated_at))), '. ', link(hashFor('changes'), P.hsChanged), ' · ', link(hashFor('spend'), P.hsCost), '.'];
}

function routineTable(rows) {
  return table([
    { label: P.colRoutine, sort: (r) => r.name, cell: (r) => plink(r.link, clean(r.name)) },
    { label: P.colHealth, sort: (r) => r.health, cell: (r) => pill(r.health) },
    { label: P.colLastRun, sort: (r) => r.last_run, cell: (r) => at(r.last_run) }], rows);
}

function needsView(dash, ctx, nowMs) {
  const doc = ctx.doc;
  const waiting = rowsOf(dash, 'waiting');
  const hb = (rowsOf(dash, 'half_built_summary') || [])[0];
  const att = attentionGroups(attentionRows(dash, doc));
  const cap = capUse(rowsOf(dash, 'eval_allowance'), rowsOf(dash, 'budget'));
  const routines = some(dash, 'routines');
  const rh = routineHealth(routines);
  const snap = snapshotMs(dash);
  const problems = (routines || []).filter((r) => r.health !== 'OK'), healthy = (routines || []).filter((r) => r.health === 'OK');
  return h('div', null,
    waiting ? panel(P.waitingHeading, waiting.length ? [h('p', { class: 'note' }, P.waitingNote), table([
      { label: P.colWhat, sort: (r) => r.item, cell: (r) => plink(r.link, clean(r.item)) },
      { label: P.colWhy, sort: (r) => r.why || '', cell: (r) => clean(r.why || '') },
      { label: P.colWhere, sort: (r) => r.where, cell: (r) => clean(r.where || '') },
      { label: P.colSince, sort: (r) => r.since, cell: (r) => at(r.since) }], waiting)] : h('p', null, P.waitingNone)) : null,
    panel(P.healthHeading, h('p', { class: 'big' }, healthStrip(doc, rh, staleHours(snap, nowMs, refreshHours(dash))))),
    panel(P.attentionHeading, [h('p', { class: 'note' }, P.attentionNote), att.length ? table([
      { label: P.colKind, sort: (r) => r.kind, cell: (r) => r.kind },
      { label: P.colSeverity, sort: (r) => r.severity, cell: (r) => pill(r.severity) },
      { label: P.colWhat, sort: (r) => r.what, cell: attentionWhat },
      { label: P.colWhere, sort: (r) => r.where || '', cell: (r) => clean(r.where || '') },
      { label: P.colAge, num: true, sort: (r) => r.age, cell: (r) => (r.age === null || r.age === undefined ? '' : r.age + ' d') }], att)
      : h('p', null, P.attentionNone)]),
    cap ? panel(P.allowanceHeading, allowanceView(cap, snap, 'eval_allowance')) : null,
    rh ? panel(P.routinesHeading, [h('p', null, P.routinesLine(rh.ok, rh.active, rh.attention, rh.fresh)),
      problems.length ? routineTable(problems.slice().sort((x, y) => (x.name < y.name ? -1 : 1))) : null,
      healthy.length ? h('details', { class: 'history' }, foldSummary(P.showHealthy(healthy.length)), routineTable(healthy)) : null]) : null,
    hb && Number(hb.open) > 0 ? h('section', { class: 'block banner', 'data-state': hb.status || 'loading' }, h('h2', null, P.hbHeading),
      h('p', { class: 'big' }, P.hbLine(n(hb.open), n(hb.high), n(hb.broken), n(hb.needs_owner), n(hb.fixed_7d))),
      h('p', { class: 'note' }, hb.checked_at ? P.hbChecked(at(hb.checked_at)) + (hb.incomplete ? P.hbIncomplete : '') : P.hbNever)) : null);
}

function usageGroup(rows, keyOf) {
  const by = new Map();
  for (const r of rows) {
    const k = keyOf(r);
    if (!by.has(k)) by.set(k, { key: k, kind: r.kind, name: r.name, repo: r.repo, week: r.week, surface: r.surface, uses: 0, sessions: null, blocked: null, overridden: null, repos: new Set(), last: '' });
    const g = by.get(k);
    g.uses += Number(r.invocations) || 0;
    for (const f of ['sessions', 'blocked', 'overridden']) if (r[f] !== null && r[f] !== undefined) g[f] = (g[f] || 0) + r[f];
    g.repos.add(r.repo);
    if (r.week > g.last) g.last = r.week;
  }
  return Array.from(by.values());
}

export function makeExt(dash, opts) {
  const now = (opts && opts.now) || Date.now;
  const asOf = (id) => asOfLine(id, snapshotMs(dash));
  const ok = (id) => !!some(dash, id);
  const usage = () => (some(dash, 'usage_rows') || []);
  const ext = {
    covers(key) {
      if (key === 'prs') return ok('open_prs') || ok('merged_prs');
      if (key === 'use') return usage().some((r) => r.kind !== 'hook_all');
      if (key === 'cost') return ok('cost_benefit_summary');
      if (key === 'runs') return ok('run_stream');
      if (key === 'issues') return ok('open_issues');
      return false;
    },
    needs: (ctx) => needsView(dash, ctx, now()),
    /* One line above every group when the snapshot is older than a refresh allows. */
    banner() {
      const snap = snapshotMs(dash);
      const every = refreshHours(dash);
      const hours = staleHours(snap, now(), every);
      return hours === null ? null : h('p', { class: 'panel failure', role: 'status' }, P.staleBanner(fmtDateTime(snap), hours, every));
    },
    summaryPanels(ctx, doc) {
      const v = conversionView(doc);
      return v ? panel(P.conversionHeading, v) : null;
    },
    summaryTiles() {
      const out = [];
      const w = rowsOf(dash, 'waiting');
      if (w) out.push(tile({ label: P.tileWaiting, value: fmtCount(w.length), note: P.tileWaitingNote, href: hashFor('needs'), tip: STRINGS.srcTip(src('waiting'), '') }));
      const rh = routineHealth(some(dash, 'routines'));
      if (rh) out.push(tile({ label: P.tileRoutines, value: rh.ok + ' of ' + rh.active, note: P.routinesLine(rh.ok, rh.active, rh.attention, rh.fresh), href: hashFor('needs') }));
      const cap = capUse(rowsOf(dash, 'eval_allowance'), rowsOf(dash, 'budget'));
      if (cap) out.push(tile({ label: P.tileAllowance, value: cap.spent.toFixed(1) + ' of ' + cap.cap.toFixed(0), note: P.tileAllowanceNote, href: hashFor('needs'),
        tip: STRINGS.srcTip(src('eval_allowance'), isFinite(parseTime(cap.readingAt)) ? fmtDateTime(parseTime(cap.readingAt)) : '') }));
      return out;
    },
    rosterWhy(ctx, model) {
      const r = (some(dash, 'roster') || []).find((x) => x.id === model);
      return r && r.why ? r.why : null;
    },
    subjectUse(ctx, name) {
      const rows = usage().filter((r) => r.kind === 'skill' && r.name === name);
      if (!rows.length) return null;
      const byRepo = usageGroup(rows, (r) => r.repo).sort((a, b) => b.uses - a.uses);
      return [h('h3', null, P.byRepoHeading), table([
        { label: P.colRepo, sort: (g) => g.repo, cell: (g) => clean(g.repo) },
        { label: P.colUses, num: true, sort: (g) => g.uses, cell: (g) => n(g.uses) },
        { label: P.colLastWeek, sort: (g) => g.last, cell: (g) => fmtWeekStart(g.last) }], byRepo)];
    },
    /* The live merged pull requests, in the document's own shape, for the changes list. */
    changePulls() {
      return (some(dash, 'merged_prs') || []).map((p) => ({ repo: p.repo, number: p.number, title: p.title, state: 'merged', created_at: p.created_at,
        merged_at: p.closed_at, url: p.url }));
    },
    impactUse() {
      const rows = usage().filter((r) => r.kind !== 'hook_all');
      const sources = some(dash, 'usage_sources');
      return [panel(P.useHeading, rows.length ? [h('p', { class: 'note' }, P.useNote), asOf('usage_rows'), table([
        { label: P.colKind, sort: (g) => g.kind, cell: (g) => (g.kind === 'hook' ? 'git hook' : clean(g.kind)) },
        { label: P.colName, sort: (g) => g.name, cell: (g) => clean(g.name) },
        { label: P.colUses, num: true, sort: (g) => g.uses, cell: (g) => n(g.uses) },
        { label: P.colSessions, num: true, sort: (g) => g.sessions, cell: (g) => n(g.sessions) },
        { label: P.colBlocked, num: true, sort: (g) => g.blocked, cell: (g) => n(g.blocked) },
        { label: P.colRedCi, num: true, sort: (g) => g.overridden, cell: (g) => n(g.overridden) },
        { label: P.colRepos, num: true, sort: (g) => g.repos.size, cell: (g) => n(g.repos.size) },
        { label: P.colLastWeek, sort: (g) => g.last, cell: (g) => fmtWeekStart(g.last) }], usageGroup(rows, (r) => r.kind + '|' + r.name).sort((a, b) => b.uses - a.uses), { tall: true }),
      h('h3', null, P.byWeekHeading), table([
        { label: P.colWeek, sort: (g) => g.week, cell: (g) => fmtWeekStart(g.week) },
        { label: P.colSurface, sort: (g) => g.surface, cell: (g) => clean(g.surface) },
        { label: P.colUses, num: true, sort: (g) => g.uses, cell: (g) => n(g.uses) },
        { label: P.colBlocked, num: true, sort: (g) => g.blocked, cell: (g) => n(g.blocked) },
        { label: P.colRedCi, num: true, sort: (g) => g.overridden, cell: (g) => n(g.overridden) }],
      usageGroup(rows.filter((r) => r.kind !== 'guidance-check'), (r) => r.week + '|' + r.surface).sort((a, b) => (a.week < b.week ? 1 : -1)), { tall: true })] : null),
      panel(P.sourcesHeading, sources ? table([
        { label: P.colFile, sort: (r) => r.file, cell: (r) => clean(r.file) }, { label: P.colSurface, cell: (r) => clean(r.surface) },
        { label: P.colScope, cell: (r) => clean(r.scope) }, { label: P.colFrom, sort: (r) => r.from, cell: (r) => at(r.from) },
        { label: P.colTo, sort: (r) => r.to, cell: (r) => at(r.to) },
        { label: P.colRead, num: true, sort: (r) => r.scanned, cell: (r) => (r.scanned === null ? '' : fmtCount(r.scanned) + ' ' + clean(r.scanned_unit || '')) },
        { label: P.colMade, sort: (r) => r.generated_at, cell: (r) => at(r.generated_at) }], sources) : null)];
    },
    cost() {
      const weeks = some(dash, 'cost_benefit_weeks');
      return panel(P.costHeading, [h('p', { class: 'note' }, P.costNote), asOf('cost_benefit_summary'), table([
        { label: P.colMeasure, cell: (r) => clean(r.label) },
        { label: P.colValue, num: true, sort: (r) => r.value, cell: (r) => (r.value === null ? STRINGS.noValue : r.key === 'cost_per_verdict' ? usd(r.value) : typeof r.value === 'number' ? fmtCount(r.value) : clean(r.value)) },
        { label: P.colTarget, cell: (r) => clean(r.target || '') },
        { label: P.colStatus, cell: (r) => (r.status ? pill(r.status) : '') },
        { label: P.colNote, cell: (r) => clean(r.note || '') }], some(dash, 'cost_benefit_summary')),
      weeks ? [h('details', { class: 'history' }, h('summary', null, P.costByWeek), table([
        { label: P.colWeek, sort: (r) => r.week, cell: (r) => fmtWeekStart(r.week) },
        { label: P.colEvalRuns, num: true, sort: (r) => r.run_count, cell: (r) => n(r.run_count) },
        { label: P.colRunPoints, num: true, sort: (r) => r.run_points_est, cell: (r) => n(r.run_points_est) },
        { label: P.colApi, num: true, sort: (r) => r.api_usd, cell: (r) => usd(r.api_usd) },
        { label: P.colThreads, num: true, sort: (r) => r.build_usd, cell: (r) => usd(r.build_usd) + (r.build_estimated ? P.estimated : '') },
        { label: P.colThreadPoints, num: true, sort: (r) => r.build_points, cell: (r) => n(r.build_points) },
        { label: P.colChanges, num: true, sort: (r) => r.changes, cell: (r) => n(r.changes) },
        { label: P.colReach, num: true, sort: (r) => r.real_work_reach, cell: (r) => n(r.real_work_reach) },
        { label: P.colMessages, num: true, sort: (r) => r.owner_messages, cell: (r) => n(r.owner_messages) }], weeks.slice().sort((a, b) => (a.week < b.week ? 1 : -1))),
      h('p', { class: 'note' }, P.estimatedNote))] : null]);
    },
    opsTop() {
      return [panel(P.routinesTable, ok('routines') ? [asOf('routines'), table([
        { label: P.colRoutine, sort: (r) => r.name, cell: (r) => plink(r.link, clean(r.name)) },
        { label: P.colDoes, cell: (r) => clean(r.what) },
        { label: P.colSchedule, cell: (r) => clean(etSchedule(r.schedule, now())) },
        { label: P.colLastRun, sort: (r) => r.last_run, cell: (r) => at(r.last_run) },
        { label: P.colHealth, sort: (r) => r.health, cell: (r) => pill(r.health) },
        { label: P.colNote, cell: (r) => clean(etSchedule(r.note || '', now())) }], some(dash, 'routines'), { cap: 10 })] : null),
      panel(P.checkinsHeading, ok('checkins') ? table([
        { label: P.colWhen, sort: (r) => r.when, cell: (r) => at(r.when) },
        { label: P.colWhat, cell: (r) => clean(r.what) }], some(dash, 'checkins')) : null)];
    },
    runs() {
      const PROBLEM = ['Failed', 'Cancelled', 'Needs approval'];
      const took = (v, r) => (v === null || v === undefined ? (r.state === 'Queued' ? 'queued' : 'running')
        : v >= 3600 ? Math.floor(v / 3600) + 'h ' + String(Math.floor((v % 3600) / 60)).padStart(2, '0') + 'm'
          : Math.floor(v / 60) + 'm ' + String(v % 60).padStart(2, '0') + 's');
      return panel(P.runsHeading, [h('p', { class: 'note' }, P.runsNote(refreshHours(dash))), asOf('run_stream'), problemsToggle(), table([
        { label: P.colWhen, cls: 'when', sort: (r) => r.at, cell: (r) => at(r.at) },
        { label: P.colState, sort: (r) => r.state, cell: (r) => pill(r.state) },
        { label: P.colWhere, sort: (r) => r.source, cell: (r) => clean(r.source || '') },
        { label: P.colRun, sort: (r) => runName(r.title, r.name), cell: (r) => plink(r.link, clean(runName(r.title, r.name))) },
        { label: P.colTook, num: true, sort: (r) => r.duration_s, cell: (r) => took(r.duration_s, r) }],
      some(dash, 'run_stream').slice().sort((a, b) => String(b.at).localeCompare(String(a.at))), { tall: true, cls: 'console', counts: (r) => PROBLEM.includes(r.state), rowAttrs: (r) => (PROBLEM.includes(r.state) ? null : { 'data-ok': '' }) })], PROBLEMS_PANEL);
    },
    prs() {
      const open = some(dash, 'open_prs') || [];
      const merged = some(dash, 'merged_prs') || [];
      return panel(P.prsHeading, [srcLine(P.srcLive, NaN), open.length ? [h('h3', null, P.openPrs), table([
        { label: STRINGS.colRepoNumber, sort: (p) => p.repo + '#' + String(p.number).padStart(9, '0'), cell: (p) => repoNumber(p.repo, p.number, p.url) },
        { label: P.colTitle, sort: (p) => p.title, cell: (p) => [plink(p.url, clean(p.title)), isLoopBranch(p.branch) ? [' ', badge('loop')] : null, ' ', plink(p.checks_url, pill(p.checks)), byLine(p.author, p.author_type) ? [' ', h('span', { class: 'sub' }, byLine(p.author, p.author_type))] : null,
          p.labels ? [' ', h('span', { class: 'sub' }, clean(p.labels))] : null] },
        { label: P.colOpened, sort: (p) => p.created_at, cell: (p) => at(p.created_at) }], open, { tall: true, cap: LIST_CAP })] : null,
      merged.length ? [h('h3', null, P.mergedPrs), prRows(merged.map((p) => Object.assign({ state: 'merged' }, p)))] : null]);
    },
    issues() {
      return panel(P.issuesHeading, [srcLine(P.srcLive, NaN), table([
        { label: STRINGS.colRepoNumber, sort: (i) => i.repo + '#' + String(i.number).padStart(9, '0'), cell: (i) => repoNumber(i.repo, i.number, i.url) },
        { label: P.colTitle, sort: (i) => i.title, cell: (i) => [plink(i.url, clean(i.title)), i.labels ? [' ', h('span', { class: 'sub' }, clean(i.labels))] : null] },
        { label: P.colUpdated, sort: (i) => i.updated_at, cell: (i) => at(i.updated_at) }],
      some(dash, 'open_issues').slice().sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at))), { tall: true, cap: LIST_CAP })]);
    },
    opsBottom() {
      return [
        panel(P.ingestsHeading, ok('eval_ingests') ? [h('p', { class: 'note' }, P.ingestsNote), table([
          { label: P.colRun, sort: (r) => r.run_id || r.message, cell: (r) => plink(r.url, clean(r.run_id || r.message)) },
          { label: P.colSaved, sort: (r) => r.ingested_at, cell: (r) => at(r.ingested_at) }], some(dash, 'eval_ingests'), { tall: true })] : null),
        panel(P.threadsHeading, ok('threads') ? threadTables(some(dash, 'threads')) : null)];
    },
    searchExtra() {
      const out = [];
      for (const p of (some(dash, 'open_prs') || []).concat(some(dash, 'merged_prs') || [])) {
        out.push({ kind: 'pr', title: p.title, url: p.url, text: [p.title, p.repo, '#' + p.number, p.branch].join(' '), detail: p.repo + ' #' + p.number });
      }
      for (const i of some(dash, 'open_issues') || []) out.push({ kind: 'issue', title: i.title, url: i.url, text: [i.title, i.repo, '#' + i.number, i.labels].join(' '), detail: i.repo + ' #' + i.number });
      return out;
    }
  };
  return ext;
}

/* Threads still going first; the finished ones fold away under their count. */
export function threadTables(threads) {
  const cols = [
    { label: P.colThread, sort: (r) => r.title, cell: (r) => plink(r.link, clean(r.title)) },
    { label: P.colState, sort: (r) => r.state, cell: (r) => pill(r.state) },
    { label: P.colActive, sort: (r) => r.last_active, cell: (r) => at(r.last_active) }];
  const open = threads.filter((r) => r.state !== 'Done'), done = threads.filter((r) => r.state === 'Done');
  return [open.length ? table(cols, open) : h('p', null, P.threadsNoneOpen), fold(P.threadsDone(done.length), done.length ? table(cols, done, { tall: true }) : null)];
}

function prRows(rows) {
  return table([
    { label: STRINGS.colRepoNumber, sort: (p) => p.repo + '#' + String(p.number).padStart(9, '0'), cell: (p) => repoNumber(p.repo, p.number, p.url) },
    { label: P.colTitle, sort: (p) => p.title, cell: (p) => plink(p.url, clean(p.title)) },
    { label: P.colMerged, sort: (p) => p.closed_at || p.created_at, cell: (p) => clean(p.state) + ' ' + at(p.closed_at || p.created_at) }],
  rows.slice().sort((a, b) => String(b.closed_at || b.created_at).localeCompare(String(a.closed_at || a.created_at))), { tall: true, cap: LIST_CAP });
}
