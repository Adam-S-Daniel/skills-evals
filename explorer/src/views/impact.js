/* Impact: real-work use of skills and git hook checks by week, pull request
   outcomes, red CI runs, and cost when the document carries it. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtUtcDay, fmtDateTime, fmtCount } from '../core/format.js';
import { h, link } from '../core/h.js';
import { skillItems } from '../core/items.js';
import { hookItems, hookWeeks, mondayOf } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { table, srcLine, panel, navLink } from './bits.js';
import { weekChart } from './weekchart.js';

const usd = (x) => (typeof x === 'number' && isFinite(x) ? '$' + x.toFixed(2) : STRINGS.noValue);
const dayOf = (d, refMs) => fmtUtcDay(Date.parse(d + 'T00:00:00Z'), refMs);

function hookWeeksView(doc, refMs) {
  const weeks = hookWeeks(doc);
  if (!weeks.length) return null;
  const old = weeks.slice().reverse();
  return [weekChart(old.map((w) => ({ label: dayOf(w.week, refMs), a: w.local.blocked, b: w.ci.blocked })), [STRINGS.colLocalBlocked, STRINGS.colCiBlocked], STRINGS.impactUseWeeks),
    table([
      { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => dayOf(w.week, refMs) },
      { label: STRINGS.colLocalRuns, num: true, sort: (w) => w.local.runs, cell: (w) => fmtCount(w.local.runs) },
      { label: STRINGS.colLocalBlocked, num: true, sort: (w) => w.local.blocked, cell: (w) => fmtCount(w.local.blocked) },
      { label: STRINGS.colCiRuns, num: true, sort: (w) => w.ci.runs, cell: (w) => fmtCount(w.ci.runs) },
      { label: STRINGS.colCiBlocked, num: true, sort: (w) => w.ci.blocked, cell: (w) => fmtCount(w.ci.blocked) }
    ], weeks)];
}

function skillUseView(doc, refMs) {
  const u = doc.usage;
  const rows = skillItems(doc).filter((s) => s.raw.usage && typeof s.raw.usage.invocations === 'number');
  if (!rows.length || !u) return null;
  return [h('p', { class: 'note' }, STRINGS.impactUseSkillsNote(fmtUtcDay(parseTime(u.from), refMs), fmtUtcDay(parseTime(u.to), refMs))),
    table([
      { label: STRINGS.colName, sort: (s) => s.name, cell: (s) => navLink(hashFor('skills', s.name), clean(s.name)) },
      { label: STRINGS.colUses, num: true, sort: (s) => s.raw.usage.invocations, cell: (s) => fmtCount(s.raw.usage.invocations) }
    ], rows.sort((a, b) => b.raw.usage.invocations - a.raw.usage.invocations || (a.name < b.name ? -1 : 1)), { tall: true })];
}

function checkUseView(doc) {
  const items = hookItems(doc).filter((it) => it.runs !== null);
  if (!items.length) return null;
  return table([
    { label: STRINGS.colCheck, sort: (it) => it.name, cell: (it) => navLink(hashFor('hooks', it.name), clean(it.name)) },
    { label: STRINGS.colRuns, num: true, sort: (it) => it.runs, cell: (it) => fmtCount(it.runs) },
    { label: STRINGS.colBlocked, num: true, sort: (it) => it.blocked, cell: (it) => fmtCount(it.blocked || 0) }
  ], items.slice().sort((a, b) => b.runs - a.runs));
}

/* Pull requests opened and merged per UTC week, from the document's activity. */
export function prWeeks(doc) {
  const a = doc.activity;
  const pulls = a && Array.isArray(a.pulls) ? a.pulls : [];
  const by = new Map();
  const add = (ts, key) => {
    const w = mondayOf(parseTime(ts));
    if (!w) return;
    if (!by.has(w)) by.set(w, { week: w, opened: 0, merged: 0 });
    by.get(w)[key] += 1;
  };
  for (const p of pulls) {
    if (!p) continue;
    add(p.created_at, 'opened');
    if (p.state === 'merged') add(p.merged_at, 'merged');
  }
  return Array.from(by.values()).sort((x, y) => (x.week < y.week ? 1 : -1));
}

function prOutcomesView(doc, refMs) {
  const a = doc.activity;
  const weeks = prWeeks(doc);
  if (!a || !weeks.length) return null;
  const repos = (Array.isArray(a.repos) ? a.repos : []).map((r) => clean(String(r).split('/').pop())).join(', ');
  return [h('p', { class: 'note' }, STRINGS.impactPrsNote(repos, fmtDateTime(parseTime(a.since)))),
    weekChart(weeks.slice().reverse().map((w) => ({ label: dayOf(w.week, refMs), a: w.opened, b: w.merged })), [STRINGS.colOpened, STRINGS.colMerged], STRINGS.impactPrs),
    table([
      { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => dayOf(w.week, refMs) },
      { label: STRINGS.colOpened, num: true, sort: (w) => w.opened, cell: (w) => fmtCount(w.opened) },
      { label: STRINGS.colMerged, num: true, sort: (w) => w.merged, cell: (w) => fmtCount(w.merged) }
    ], weeks)];
}

export const RED = ['failure', 'timed_out', 'startup_failure'];

function redRunsView(doc, refMs) {
  const a = doc.activity;
  if (!a || !Array.isArray(a.runs)) return null;
  const red = a.runs.filter((r) => r && RED.includes(r.conclusion)).sort((x, y) => (x.created_at < y.created_at ? 1 : -1));
  return [h('p', { class: 'note' }, STRINGS.impactRedNote), red.length ? table([
    { label: STRINGS.colWhen, sort: (r) => r.created_at, cell: (r) => fmtDateTime(parseTime(r.created_at)) },
    { label: STRINGS.colRepo, sort: (r) => r.repo, cell: (r) => clean(String(r.repo).split('/').pop()) },
    { label: STRINGS.colWorkflow, sort: (r) => r.workflow, cell: (r) => link(r.url, clean(r.workflow || r.title || STRINGS.unknown)) },
    { label: STRINGS.colState, sort: (r) => r.conclusion, cell: (r) => clean(r.conclusion) }
  ], red) : h('p', null, STRINGS.impactRedNone)];
}

function spendView(doc, refMs) {
  const s = doc.spend;
  if (!s || !Array.isArray(s.weeks) || !s.weeks.length) return null;
  return [h('p', { class: 'note' }, STRINGS.impactSpendNote),
    s.generated_at ? srcLine(STRINGS.srcDoc, parseTime(s.generated_at)) : null,
    table([
      { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => dayOf(w.week, refMs) },
      { label: STRINGS.colEvalRuns, num: true, sort: (w) => w.eval_runs, cell: (w) => (w.eval_runs === null ? STRINGS.noValue : fmtCount(w.eval_runs)) },
      { label: STRINGS.colMeter, num: true, sort: (w) => w.plan_meter_points, cell: (w) => (w.plan_meter_points === null ? STRINGS.noValue : w.plan_meter_points.toFixed(1)) },
      { label: STRINGS.colApi, num: true, sort: (w) => w.api_usd, cell: (w) => usd(w.api_usd) },
      { label: STRINGS.colThreads, num: true, sort: (w) => w.thread_spend_usd, cell: (w) => usd(w.thread_spend_usd) },
      { label: STRINGS.colPerVerdict, num: true, sort: (w) => w.cost_per_verdict, cell: (w) => usd(w.cost_per_verdict) }
    ], s.weeks)];
}

export function impactView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const ext = ctx && ctx.ext;
  const covers = (k) => !!(ext && ext.covers && ext.covers(k));
  return h('div', null,
    srcLine(STRINGS.srcDoc, refMs),
    panel(STRINGS.impactUseWeeks, hookWeeksView(doc, refMs)),
    // The private usage table covers both lists, private repos included.
    covers('use') ? ext.impactUse(ctx) : [panel(STRINGS.impactUseChecks, checkUseView(doc)), panel(STRINGS.impactUseSkills, skillUseView(doc, refMs))],
    covers('pr-outcomes') ? ext.prOutcomes(ctx) : panel(STRINGS.impactPrs, prOutcomesView(doc, refMs)),
    covers('red-runs') ? ext.redRuns(ctx) : panel(STRINGS.impactRed, redRunsView(doc, refMs)),
    covers('cost') ? ext.cost(ctx) : panel(STRINGS.impactSpend, spendView(doc, refMs)));
}
