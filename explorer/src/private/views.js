/* The private build's overlays: the Needs you group and the panels each
   shared group adds from the dashboard's own datasets. Every panel hides
   itself when its datasets are empty, so a dashboard with only the explorer
   dataset shows the public views alone. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDateTime, fmtCount } from '../core/format.js';
import { h } from '../core/h.js';
import { hashFor } from '../core/route.js';
import { table, panel, srcLine, tile, badge } from '../views/bits.js';
import { alertText } from '../views/alerts.js';
import { trendingView } from '../views/trending.js';
import { LOOP_TITLE } from '../views/loop.js';
import { problemsToggle } from '../views/ops.js';
import { rowsOf, some } from './datasets.js';
import { P } from './strings.js';
import { conversionView } from './conversion.js';
import { isTrending, alertKindLabel } from '../core/stats.js';

const at = (s) => (s ? fmtDateTime(parseTime(s)) : STRINGS.noValue);
const n = (v) => (v === null || v === undefined ? '' : fmtCount(v));
const usd = (v) => (typeof v === 'number' ? '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : STRINGS.noValue);
const SAFE = /^https:\/\/(github\.com|claude\.ai)\//;
export function plink(url, text) {
  return typeof url === 'string' && SAFE.test(url) ? h('a', { href: url, rel: 'noopener', target: '_blank' }, text) : text;
}
function pill(text) {
  const t = String(text || '');
  const kind = /^(Done|OK|Met|Succeeded|Passed|ok|clear)$/i.test(t) ? 'good'
    : /stalled|stopped|not started|failed|^(high|broken)$/i.test(t) ? 'bad'
      : /waiting|partly|needs|not yet|in progress|^(Running|Queued|medium)$/i.test(t) ? 'warn' : '';
  return h('span', { class: 'st ' + kind }, clean(t));
}
const src = (id) => P.srcSnapshot(id);
const isLoopBranch = (b) => /^(eval-improve|eval-guidance-improve|draft-skill|retire-skill|retire-guidance)\//.test(String(b || ''));

/* Test use this week against the cap, from eval_allowance and budget. */
export function capUse(allowance, budget) {
  const a = (allowance && allowance[0]) || null;
  if (!a || !budget) return null;
  const b = {};
  budget.forEach((r) => { b[r.setting] = r.value; });
  const cap = (Number(b.weekly_cap) || 0) * 100;
  const left = Math.max(0, cap - (Number(a.points) || 0));
  return { spent: Number(a.points) || 0, cap, stop: (Number(b.stop_when_account_above) || 0) * 100, accountUsed: a.account_week_used,
    room: Math.max(left, Number(a.pace_room_points) || 0), reservation: ((Number(b.per_run_cap) || 0) + (Number(b.per_run_overrun) || 0)) * 100,
    readingAt: a.account_reading_at, resetsAt: a.week_resets_at };
}

export function routineHealth(routines) {
  if (!routines) return null;
  const active = routines.filter((r) => r.health !== 'Retired');
  const fresh = active.filter((r) => r.health === 'Not run yet').length;
  const ok = active.filter((r) => r.health === 'OK').length;
  return { active: active.length - fresh, ok, attention: active.length - fresh - ok };
}

function meter(value, max, mark) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return h('div', { class: 'meter' }, h('div', { class: 'fill' + (value > max ? ' over' : ''), style: 'width:' + pct.toFixed(1) + '%' }),
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
    rows.push({ kind: P.kindHalfBuilt(r.kind), severity: r.severity, what: r.title, url: r.url, where: r.repo, age: r.age_days });
  }
  for (const a of Array.isArray(doc.alerts) ? doc.alerts : []) {
    if (!a) continue;
    // A regression on an undecided subject is trending toward removal, not an
    // item that needs attention: its own table. On a decided one it is listed.
    if (isTrending(doc, a)) continue;
    const k = alertKindLabel(doc, a);
    rows.push({ kind: P.kindAlert(k), severity: 'medium', what: alertWhat(a), url: a.url, where: a.subject, age: null });
  }
  const f = doc.fires_without_results;
  if (f && Number.isInteger(f.without_results) && (f.without_results || f.rejected) && typeof f.since === 'string') {
    rows.push({ kind: P.kindFires, severity: 'medium', what: STRINGS.firesLine(f.without_results, Number.isInteger(f.counted) ? f.counted : null, at(f.since), Array.isArray(f.sweeps) ? f.sweeps.length : 0, f.rejected || 0), url: null, where: null, age: null });
  }
  const q = doc.fixture_queue;
  for (const x of q && Array.isArray(q.findings) ? q.findings : []) {
    if (x) rows.push({ kind: P.kindFixture(x.kind || ''), severity: x.severity || 'unknown', what: clean(x.subject || x.finding_id || ''), url: x.url, where: null, age: null });
  }
  const order = { high: 0, medium: 1, low: 2 };
  return rows.sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
}

function needsView(dash, ctx) {
  const doc = ctx.doc;
  const waiting = some(dash, 'waiting');
  const hb = (rowsOf(dash, 'half_built_summary') || [])[0];
  const att = attentionRows(dash, doc);
  const cap = capUse(rowsOf(dash, 'eval_allowance'), rowsOf(dash, 'budget'));
  const routines = some(dash, 'routines');
  const rh = routineHealth(routines);
  return h('div', null,
    hb ? h('section', { class: 'block banner', 'data-state': hb.status || 'loading' }, h('h2', null, P.hbHeading),
      srcLine(src('half_built_summary'), parseTime(hb.checked_at)),
      h('p', { class: 'big' }, P.hbLine(n(hb.open), n(hb.high), n(hb.broken), n(hb.needs_owner), n(hb.fixed_7d))),
      h('p', { class: 'note' }, hb.checked_at ? P.hbChecked(at(hb.checked_at)) + (hb.incomplete ? P.hbIncomplete : '') : P.hbNever)) : null,
    panel(P.waitingHeading, waiting ? [h('p', { class: 'note' }, P.waitingNote), table([
      { label: P.colWhat, sort: (r) => r.item, cell: (r) => clean(r.item) },
      { label: P.colWhere, sort: (r) => r.where, cell: (r) => plink(r.link, clean(r.where || '')) },
      { label: P.colSince, sort: (r) => r.since, cell: (r) => at(r.since) }], waiting)] : null),
    panel(P.attentionHeading, [h('p', { class: 'note' }, P.attentionNote), att.length ? table([
      { label: P.colKind, sort: (r) => r.kind, cell: (r) => r.kind },
      { label: P.colSeverity, sort: (r) => r.severity, cell: (r) => pill(r.severity) },
      { label: P.colWhat, sort: (r) => r.what, cell: (r) => plink(r.url, clean(r.what)) },
      { label: P.colWhere, sort: (r) => r.where || '', cell: (r) => clean(r.where || '') },
      { label: P.colAge, num: true, sort: (r) => r.age, cell: (r) => (r.age === null || r.age === undefined ? '' : r.age + ' d') }], att, { tall: true })
      : h('p', null, P.attentionNone)]),
    trendingView(doc, 'all'),
    cap ? panel(P.allowanceHeading, [srcLine(src('eval_allowance'), parseTime(cap.readingAt)),
      h('p', null, P.allowanceUse(cap.spent.toFixed(1), cap.cap.toFixed(0))), meter(cap.spent, cap.cap),
      cap.accountUsed !== null && cap.accountUsed !== undefined ? [h('p', null, P.allowanceAccount(Math.round(cap.accountUsed), cap.stop.toFixed(0))), meter(cap.accountUsed, 100, cap.stop)] : null,
      h('p', { class: 'note' }, P.allowanceRoom(cap.room.toFixed(1), cap.reservation.toFixed(1))),
      h('p', { class: 'note' }, P.allowanceReading(at(cap.readingAt), at(cap.resetsAt)))]) : null,
    rh ? panel(P.routinesHeading, [h('p', null, P.routinesLine(rh.ok, rh.active, rh.attention)), table([
      { label: P.colRoutine, sort: (r) => r.name, cell: (r) => plink(r.link, clean(r.name)) },
      { label: P.colHealth, sort: (r) => r.health, cell: (r) => pill(r.health) },
      { label: P.colLastRun, sort: (r) => r.last_run, cell: (r) => at(r.last_run) }], routines)]) : null);
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

const OUTCOMES = ['prs_opened', 'prs_merged', 'agent_prs_merged', 'prs_closed_unmerged', 'prs_reverted', 'ci_red_after'];

export function makeExt(dash) {
  const ok = (id) => !!some(dash, id);
  const usage = () => (some(dash, 'usage_rows') || []);
  const ext = {
    covers(key) {
      if (key === 'loop-prs' || key === 'prs') return ok('open_prs') || ok('merged_prs');
      if (key === 'use') return usage().some((r) => r.kind !== 'repo' && r.kind !== 'hook_all');
      if (key === 'pr-outcomes') return usage().some((r) => r.kind === 'repo');
      if (key === 'red-runs') return ok('ci_red_runs');
      if (key === 'cost') return ok('cost_benefit_summary');
      if (key === 'runs') return ok('run_stream');
      if (key === 'issues') return ok('open_issues');
      return false;
    },
    needs: (ctx) => needsView(dash, ctx),
    summaryPanels(ctx, doc) {
      const v = conversionView(doc);
      return v ? panel(P.conversionHeading, v) : null;
    },
    summaryTiles() {
      const out = [];
      const w = rowsOf(dash, 'waiting');
      if (w) out.push(tile({ label: P.tileWaiting, value: fmtCount(w.length), note: P.tileWaitingNote, href: hashFor('needs'), tip: STRINGS.srcTip(src('waiting'), '') }));
      const rh = routineHealth(some(dash, 'routines'));
      if (rh) out.push(tile({ label: P.tileRoutines, value: rh.ok + ' of ' + rh.active, note: P.routinesLine(rh.ok, rh.active, rh.attention), href: hashFor('needs') }));
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
        { label: P.colLastWeek, sort: (g) => g.last, cell: (g) => g.last }], byRepo)];
    },
    loopStages() {
      const st = some(dash, 'loop_stages');
      if (!st) return null;
      return [srcLine(src('loop_stages'), NaN), table([
        { label: P.colStep, sort: (r) => r.kind, cell: (r) => clean(r.kind) },
        { label: P.colStage, sort: (r) => r.stage, cell: (r) => plink(r.link, clean(r.stage)) },
        { label: P.colStatus, sort: (r) => r.status, cell: (r) => pill(r.status) },
        { label: P.colDoes, cell: (r) => clean(r.what) },
        { label: P.colGaps, cell: (r) => clean(r.gaps) }], st), h('p', { class: 'note' }, STRINGS.loopStagesNote)];
    },
    loopTop() {
      const threads = new Map((some(dash, 'threads') || []).map((t) => [t.title, t]));
      const lanes = some(dash, 'loop_lanes');
      return [
        // The lanes are built; their builder threads are history, so the
        // table starts folded under the gaps it closed.
        panel(P.lanesHeading, lanes ? h('details', { class: 'history' }, h('summary', null, P.lanesShow(lanes.length)), table([
          { label: P.colLane, sort: (r) => r.lane, cell: (r) => clean(r.lane) },
          { label: P.colThread, sort: (r) => r.thread, cell: (r) => plink(r.link, clean(r.thread)) },
          { label: P.colBuilds, cell: (r) => clean(r.does) },
          { label: P.colLatest, cell: (r) => plink(r.latest_link, clean(r.latest)) },
          { label: P.colState, sort: (r) => (threads.get(r.thread) || {}).state || '', cell: (r) => pill((threads.get(r.thread) || {}).state || '') },
          { label: P.colActive, sort: (r) => (threads.get(r.thread) || {}).last_active || '', cell: (r) => at((threads.get(r.thread) || {}).last_active) }], lanes)) : null),
        panel(P.gapsHeading, ok('loop_gaps') ? table([
          { label: P.colGap, sort: (r) => r.gap, cell: (r) => clean(r.gap) },
          { label: STRINGS.colTitle, sort: (r) => r.title, cell: (r) => plink(r.link, clean(r.title)) },
          { label: P.colStatus, sort: (r) => r.status, cell: (r) => pill(r.status) },
          { label: P.colOwner, sort: (r) => r.owner, cell: (r) => clean(r.owner) }], some(dash, 'loop_gaps')) : null),
        panel(P.gridHeading, ok('loop_grid') ? table([
          { label: P.colStep, cell: (r) => clean(r.stage) }, { label: P.colSkills, cell: (r) => clean(r.skills) },
          { label: P.colGuidance, cell: (r) => clean(r.guidance) }, { label: P.colMemories, cell: (r) => clean(r.memories) }], some(dash, 'loop_grid')) : null),
        panel(P.gateHeading, ok('gate') ? table([
          { label: P.colCondition, cell: (r) => plink(r.link, clean(r.condition)) },
          { label: P.colStatus, sort: (r) => r.status, cell: (r) => pill(r.status) },
          { label: P.colDetail, cell: (r) => clean(r.detail) }], some(dash, 'gate')) : null)];
    },
    loopPrs() {
      const rows = (some(dash, 'open_prs') || []).filter((p) => isLoopBranch(p.branch)).map((p) => Object.assign({ state: 'open' }, p))
        .concat((some(dash, 'merged_prs') || []).filter((p) => LOOP_TITLE.test(String(p.title || ''))).map((p) => Object.assign({ state: 'merged' }, p)));
      return panel(P.loopPrsHeading, rows.length ? [srcLine(P.srcLive, NaN), h('p', { class: 'note' }, P.loopPrsNote), prRows(rows)] : null);
    },
    impactUse() {
      const rows = usage().filter((r) => r.kind !== 'repo' && r.kind !== 'hook_all');
      const sources = some(dash, 'usage_sources');
      return [panel(P.useHeading, rows.length ? [h('p', { class: 'note' }, P.useNote), srcLine(src('usage_rows'), NaN), table([
        { label: P.colKind, sort: (g) => g.kind, cell: (g) => (g.kind === 'hook' ? 'git hook' : clean(g.kind)) },
        { label: P.colName, sort: (g) => g.name, cell: (g) => clean(g.name) },
        { label: P.colUses, num: true, sort: (g) => g.uses, cell: (g) => n(g.uses) },
        { label: P.colSessions, num: true, sort: (g) => g.sessions, cell: (g) => n(g.sessions) },
        { label: P.colBlocked, num: true, sort: (g) => g.blocked, cell: (g) => n(g.blocked) },
        { label: P.colRedCi, num: true, sort: (g) => g.overridden, cell: (g) => n(g.overridden) },
        { label: P.colRepos, num: true, sort: (g) => g.repos.size, cell: (g) => n(g.repos.size) },
        { label: P.colLastWeek, sort: (g) => g.last, cell: (g) => g.last }], usageGroup(rows, (r) => r.kind + '|' + r.name).sort((a, b) => b.uses - a.uses), { tall: true }),
      h('h3', null, P.byWeekHeading), table([
        { label: P.colWeek, sort: (g) => g.week, cell: (g) => g.week },
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
    prOutcomes() {
      const oc = usage().filter((r) => r.kind === 'repo');
      const sum = (rs, keyOf) => {
        const by = new Map();
        for (const r of rs) {
          const k = keyOf(r);
          if (!by.has(k)) by.set(k, { key: k });
          const g = by.get(k);
          for (const f of OUTCOMES) if (r[f] !== null && r[f] !== undefined) g[f] = (g[f] || 0) + r[f];
        }
        return Array.from(by.values());
      };
      const cols = (first) => [first].concat(OUTCOMES.map((f) => ({ label: P.outcomeCols[f], num: true, sort: (g) => g[f], cell: (g) => n(g[f]) })));
      return panel(P.outcomesHeading, [h('p', { class: 'note' }, P.outcomesNote), srcLine(src('usage_rows'), NaN),
        table(cols({ label: P.colRepo, sort: (g) => g.key, cell: (g) => clean(g.key) }), sum(oc, (r) => r.repo).sort((a, b) => (b.prs_opened || 0) - (a.prs_opened || 0))),
        h('h3', null, P.byWeekHeading),
        table(cols({ label: P.colWeek, sort: (g) => g.key, cell: (g) => g.key }), sum(oc, (r) => r.week).sort((a, b) => (a.key < b.key ? 1 : -1)))]);
    },
    redRuns() {
      return panel(P.redHeading, [h('p', { class: 'note' }, P.redNote), table([
        { label: P.colWeek, sort: (r) => r.week, cell: (r) => r.week },
        { label: P.colRepo, sort: (r) => r.repo, cell: (r) => clean(r.repo) },
        { label: P.colWhen, sort: (r) => r.created_at, cell: (r) => at(r.created_at) },
        { label: P.colResult, sort: (r) => r.conclusion, cell: (r) => clean(r.conclusion || '') },
        { label: P.colRun, cell: (r) => plink(r.url, r.url ? P.run : '') }], some(dash, 'ci_red_runs').slice().sort((a, b) => String(b.created_at || b.week).localeCompare(String(a.created_at || a.week))), { tall: true })]);
    },
    cost() {
      const weeks = some(dash, 'cost_benefit_weeks');
      return panel(P.costHeading, [h('p', { class: 'note' }, P.costNote), srcLine(src('cost_benefit_summary'), NaN), table([
        { label: P.colMeasure, cell: (r) => clean(r.label) },
        { label: P.colValue, num: true, sort: (r) => r.value, cell: (r) => (r.value === null ? STRINGS.noValue : r.key === 'cost_per_verdict' ? usd(r.value) : typeof r.value === 'number' ? fmtCount(r.value) : clean(r.value)) },
        { label: P.colTarget, cell: (r) => clean(r.target || '') },
        { label: P.colStatus, cell: (r) => (r.status ? pill(r.status) : '') },
        { label: P.colNote, cell: (r) => clean(r.note || '') }], some(dash, 'cost_benefit_summary')),
      weeks ? [h('h3', null, P.byWeekHeading), table([
        { label: P.colWeek, sort: (r) => r.week, cell: (r) => r.week },
        { label: P.colEvalRuns, num: true, sort: (r) => r.run_count, cell: (r) => n(r.run_count) },
        { label: P.colRunPoints, num: true, sort: (r) => r.run_points_est, cell: (r) => n(r.run_points_est) },
        { label: P.colApi, num: true, sort: (r) => r.api_usd, cell: (r) => usd(r.api_usd) },
        { label: P.colThreads, num: true, sort: (r) => r.build_usd, cell: (r) => usd(r.build_usd) + (r.build_estimated ? P.estimated : '') },
        { label: P.colThreadPoints, num: true, sort: (r) => r.build_points, cell: (r) => n(r.build_points) },
        { label: P.colChanges, num: true, sort: (r) => r.changes, cell: (r) => n(r.changes) },
        { label: P.colReach, num: true, sort: (r) => r.real_work_reach, cell: (r) => n(r.real_work_reach) },
        { label: P.colMessages, num: true, sort: (r) => r.owner_messages, cell: (r) => n(r.owner_messages) },
        { label: P.colDecisions, num: true, sort: (r) => r.decisions, cell: (r) => n(r.decisions) }], weeks.slice().sort((a, b) => (a.week < b.week ? 1 : -1))),
      h('p', { class: 'note' }, P.estimatedNote)] : null]);
    },
    opsTop() {
      return [panel(P.routinesTable, ok('routines') ? [srcLine(src('routines'), NaN), table([
        { label: P.colRoutine, sort: (r) => r.name, cell: (r) => plink(r.link, clean(r.name)) },
        { label: P.colDoes, cell: (r) => clean(r.what) },
        { label: P.colSchedule, cell: (r) => clean(r.schedule) },
        { label: P.colLastRun, sort: (r) => r.last_run, cell: (r) => at(r.last_run) },
        { label: P.colHealth, sort: (r) => r.health, cell: (r) => pill(r.health) },
        { label: P.colNote, cell: (r) => clean(r.note || '') }], some(dash, 'routines'))] : null),
      panel(P.checkinsHeading, ok('checkins') ? table([
        { label: P.colWhen, sort: (r) => r.when, cell: (r) => at(r.when) },
        { label: P.colWhat, cell: (r) => clean(r.what) }], some(dash, 'checkins')) : null)];
    },
    runs() {
      const PROBLEM = ['Failed', 'Cancelled', 'Needs approval'];
      const took = (v, r) => (v === null || v === undefined ? (r.state === 'Queued' ? 'queued' : 'running')
        : v >= 3600 ? Math.floor(v / 3600) + 'h ' + String(Math.floor((v % 3600) / 60)).padStart(2, '0') + 'm'
          : Math.floor(v / 60) + 'm ' + String(v % 60).padStart(2, '0') + 's');
      return panel(P.runsHeading, [h('p', { class: 'note' }, P.runsNote), srcLine(src('run_stream'), NaN), problemsToggle(), table([
        { label: P.colWhen, cls: 'when', sort: (r) => r.at, cell: (r) => at(r.at) },
        { label: P.colState, sort: (r) => r.state, cell: (r) => pill(r.state) },
        { label: P.colWhere, sort: (r) => r.source, cell: (r) => clean(r.source || '') },
        { label: P.colJob, sort: (r) => r.name, cell: (r) => clean(r.name || '') },
        { label: P.colRun, sort: (r) => r.title, cell: (r) => plink(r.link, clean(r.title || '')) },
        { label: P.colTook, num: true, sort: (r) => r.duration_s, cell: (r) => took(r.duration_s, r) }],
      some(dash, 'run_stream').slice().sort((a, b) => String(b.at).localeCompare(String(a.at))), { tall: true, cls: 'console', rowAttrs: (r) => (PROBLEM.includes(r.state) ? null : { 'data-ok': '' }) })]);
    },
    prs() {
      const open = some(dash, 'open_prs') || [];
      const merged = some(dash, 'merged_prs') || [];
      return panel(P.prsHeading, [srcLine(P.srcLive, NaN), open.length ? [h('h3', null, P.openPrs), table([
        { label: P.colRepo, sort: (p) => p.repo, cell: (p) => clean(p.repo) },
        { label: P.colNumber, num: true, sort: (p) => p.number, cell: (p) => plink(p.url, '#' + p.number) },
        { label: P.colTitle, sort: (p) => p.title, cell: (p) => [plink(p.url, clean(p.title)), isLoopBranch(p.branch) ? [' ', badge('loop')] : null] },
        { label: P.colOpenedBy, sort: (p) => p.author, cell: (p) => clean(String(p.author || '').replace('[bot]', ' (bot)')) },
        { label: P.colOpened, sort: (p) => p.created_at, cell: (p) => at(p.created_at) },
        { label: P.colChecks, sort: (p) => p.checks, cell: (p) => plink(p.checks_url, pill(p.checks)) },
        { label: P.colLabels, cell: (p) => clean(p.labels || '') }], open, { tall: true })] : null,
      merged.length ? [h('h3', null, P.mergedPrs), prRows(merged.map((p) => Object.assign({ state: 'merged' }, p)))] : null]);
    },
    issues() {
      return panel(P.issuesHeading, [srcLine(P.srcLive, NaN), table([
        { label: P.colRepo, sort: (i) => i.repo, cell: (i) => clean(i.repo) },
        { label: P.colNumber, num: true, sort: (i) => i.number, cell: (i) => plink(i.url, '#' + i.number) },
        { label: P.colTitle, sort: (i) => i.title, cell: (i) => plink(i.url, clean(i.title)) },
        { label: P.colLabels, cell: (i) => clean(i.labels || '') },
        { label: P.colUpdated, sort: (i) => i.updated_at, cell: (i) => at(i.updated_at) }],
      some(dash, 'open_issues').slice().sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at))), { tall: true })]);
    },
    opsBottom() {
      return [
        panel(P.ingestsHeading, ok('eval_ingests') ? [h('p', { class: 'note' }, P.ingestsNote), table([
          { label: P.colRun, sort: (r) => r.run_id || r.message, cell: (r) => plink(r.url, clean(r.run_id || r.message)) },
          { label: P.colSaved, sort: (r) => r.ingested_at, cell: (r) => at(r.ingested_at) }], some(dash, 'eval_ingests'), { tall: true })] : null),
        panel(P.cleanupHeading, ok('cleanup') ? table([
          { label: STRINGS.colNumber, sort: (r) => r.id, cell: (r) => plink(r.link, clean(r.id)) },
          { label: P.colItem, cell: (r) => clean(r.item) }, { label: P.colDoneWhen, cell: (r) => clean(r.done_when) },
          { label: P.colStatus, sort: (r) => r.status, cell: (r) => pill(r.status) }, { label: P.colDetail, cell: (r) => clean(r.detail || '') }], some(dash, 'cleanup')) : null),
        panel(P.decisionsHeading, ok('decisions') ? table([
          { label: P.colDate, sort: (r) => r.date, cell: (r) => clean(r.date) },
          { label: P.colDecision, cell: (r) => clean(r.decision) },
          { label: P.colRecord, cell: (r) => plink(r.link, /github\.com/.test(String(r.link)) ? String(r.link).replace(/^https:\/\/github\.com\/[^/]+\//, '').replace(/\/(pull|issues)\//, '#') : P.thread) }],
        some(dash, 'decisions').slice().sort((a, b) => String(b.date).localeCompare(String(a.date)))) : null),
        panel(P.threadsHeading, ok('threads') ? table([
          { label: P.colThread, sort: (r) => r.title, cell: (r) => plink(r.link, clean(r.title)) },
          { label: P.colState, sort: (r) => r.state, cell: (r) => pill(r.state) },
          { label: P.colActive, sort: (r) => r.last_active, cell: (r) => at(r.last_active) }], some(dash, 'threads')) : null)];
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

function prRows(rows) {
  return table([
    { label: P.colRepo, sort: (p) => p.repo, cell: (p) => clean(p.repo) },
    { label: P.colNumber, num: true, sort: (p) => p.number, cell: (p) => plink(p.url, '#' + p.number) },
    { label: P.colTitle, sort: (p) => p.title, cell: (p) => plink(p.url, clean(p.title)) },
    { label: P.colState, sort: (p) => p.state, cell: (p) => clean(p.state) },
    { label: P.colMerged, sort: (p) => p.closed_at || p.created_at, cell: (p) => at(p.closed_at || p.created_at) }],
  rows.slice().sort((a, b) => String(b.closed_at || b.created_at).localeCompare(String(a.closed_at || a.created_at))), { tall: true });
}
