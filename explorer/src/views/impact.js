/* Spend and use: what the loop cost, what agents made (checks, skills,
   guidance sections), and real-work use of skills and git hook checks by week. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtUtcDay, fmtDateTime, fmtCount, fmtUsd } from '../core/format.js';
import { h, link } from '../core/h.js';
import { skillItems } from '../core/items.js';
import { hookItems, hookWeeks, cloudCounted } from '../core/hooks.js';
import { cloudNote } from './hooks.js';
import { hashFor } from '../core/route.js';
import { table, panel, navLink, rangeLine, srcLineFor } from './bits.js';
import { noUseShare } from './utility.js';
import { weekChart } from './weekchart.js';

const usd = (x) => (typeof x === 'number' && isFinite(x) ? fmtUsd(x) : STRINGS.noValue);
const dayOf = (d, refMs) => fmtUtcDay(Date.parse(d + 'T00:00:00Z'), refMs);

function hookWeeksView(doc, refMs) {
  const weeks = hookWeeks(doc);
  if (!weeks.length) return null;
  const old = weeks.slice().reverse();
  const cloud = cloudCounted(doc) === true;
  return [weekChart(old.map((w) => ({ label: dayOf(w.week, refMs), a: w.local.blocked + (cloud ? w.cloud.blocked : 0), b: w.ci.blocked })), [cloud ? STRINGS.colLocalCloudBlocked : STRINGS.colLocalBlocked, STRINGS.colCiBlocked], STRINGS.impactUseWeeks, STRINGS.weekTitles.hooks, [STRINGS.weekDefs.local, STRINGS.weekDefs.ci]),
    table([
      { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => dayOf(w.week, refMs) },
      { label: STRINGS.colLocalRuns, num: true, sort: (w) => w.local.runs, cell: (w) => fmtCount(w.local.runs) },
      { label: STRINGS.colLocalBlocked, num: true, sort: (w) => w.local.blocked, cell: (w) => fmtCount(w.local.blocked) },
      { label: STRINGS.colCiRuns, num: true, sort: (w) => w.ci.runs, cell: (w) => fmtCount(w.ci.runs) },
      { label: STRINGS.colCiBlocked, num: true, sort: (w) => w.ci.blocked, cell: (w) => fmtCount(w.ci.blocked) },
      cloud ? { label: STRINGS.colCloudRuns, num: true, sort: (w) => w.cloud.runs, cell: (w) => fmtCount(w.cloud.runs) } : null,
      cloud ? { label: STRINGS.colCloudBlocked, num: true, sort: (w) => w.cloud.blocked, cell: (w) => fmtCount(w.cloud.blocked) } : null
    ].filter(Boolean), weeks), cloudNote(doc)];
}

function skillUseView(doc, refMs) {
  const u = doc.usage;
  const rows = skillItems(doc).filter((s) => s.raw.usage && typeof s.raw.usage.invocations === 'number');
  if (!rows.length || !u) return null;
  return [srcLineFor(doc, 'usage'), h('p', { class: 'note' }, STRINGS.impactUseSkillsNote(fmtUtcDay(parseTime(u.from), refMs), fmtUtcDay(parseTime(u.to), refMs))),
    table([
      { label: STRINGS.colName, sort: (s) => s.name, cell: (s) => navLink(hashFor('skills', s.name), clean(s.name)) },
      { label: STRINGS.colUses, num: true, sort: (s) => s.raw.usage.invocations, cell: (s) => fmtCount(s.raw.usage.invocations) }
    ], rows.sort((a, b) => b.raw.usage.invocations - a.raw.usage.invocations || (a.name < b.name ? -1 : 1)), { tall: true })];
}

function checkUseView(doc) {
  const items = hookItems(doc).filter((it) => it.runs !== null || it.blocked);
  if (!items.length) return null;
  return table([
    { label: STRINGS.colCheck, sort: (it) => it.name, cell: (it) => navLink(hashFor('hooks', it.name), clean(it.name)) },
    { label: STRINGS.colRuns, num: true, sort: (it) => (it.runs !== null ? it.runs : it.runsCounted), cell: (it) => (it.runs !== null ? fmtCount(it.runs) : STRINGS.runsNotCounted) },
    { label: STRINGS.colBlocked, num: true, sort: (it) => it.blocked, cell: (it) => fmtCount(it.blocked || 0) }
  ], items.slice().sort((a, b) => (b.runs !== null ? b.runs : b.runsCounted) - (a.runs !== null ? a.runs : a.runsCounted)));
}

/* "Since Oct 19: $5,541.65 for 12 decided verdicts, $461.80 each (tests ..., building ..., API ...)",
   from spend.total; null for a document without one. */
export function spendTotalLine(s) {
  const t = s && s.total;
  if (!t || typeof t !== 'object' || typeof t.usd !== 'number') return null;
  return h('p', null, STRINGS.impactSpendTotal(dayOf(t.since, NaN), usd(t.usd), fmtCount(t.verdicts || 0),
    typeof t.cost_per_verdict === 'number' ? usd(t.cost_per_verdict) : STRINGS.noValue, usd(t.run_usd), usd(t.thread_spend_usd), usd(t.api_usd)));
}

/* The two newest weeks side by side: tests, building (threads), API and their
   total in dollars, and the plan points the tests used. A part a week does not
   carry reads as no value, and so does the total then. */
export function spendWeeks(doc) {
  const s = doc.spend;
  const weeks = s && Array.isArray(s.weeks) ? s.weeks.filter((w) => w && typeof w.week === 'string').slice().sort((a, b) => (a.week < b.week ? 1 : -1)) : [];
  const part = (w, k) => (w && typeof w[k] === 'number' && isFinite(w[k]) ? w[k] : null);
  const row = (w) => {
    const tests = part(w, 'run_usd'), build = part(w, 'thread_spend_usd'), api = part(w, 'api_usd');
    return { week: w.week, tests, build, api, total: tests === null || build === null || api === null ? null : tests + build + api, points: part(w, 'plan_meter_points') };
  };
  return weeks.slice(0, 2).map(row);
}

/* The week's boundary as Eastern time: a spend week starts Monday 17:00 UTC. */
const WEEK_MS = 7 * 86400000;
const weekStart = (w) => fmtDateTime(Date.parse(w + 'T17:00:00Z'));
/* "this" for the week that contains the data's time, "last" for the one before
   it, else a plain "Week": a page of old data does not call an old week this one. */
const weekWhich = (w, refMs) => {
  const from = Date.parse(w + 'T17:00:00Z');
  return refMs >= from && refMs < from + WEEK_MS ? 'this' : refMs - WEEK_MS >= from && refMs - WEEK_MS < from + WEEK_MS ? 'last' : '';
};

/* One panel for the loop's money: this week and last week side by side, the
   share of test dollars that bought nothing, and every week below. */
function spendView(doc, refMs) {
  const s = doc.spend;
  if (!s || !Array.isArray(s.weeks) || !s.weeks.length) return null;
  const two = spendWeeks(doc);
  const share = noUseShare(doc, refMs);
  const cell = (r, k) => (r && r[k] !== null ? usd(r[k]) : STRINGS.noValue);
  const rows = [{ label: STRINGS.spendTests, k: 'tests' }, { label: STRINGS.spendBuilding, k: 'build' }, { label: STRINGS.spendApi, k: 'api' }, { label: STRINGS.spendTotal, k: 'total' }];
  return [h('p', { class: 'note' }, STRINGS.impactSpendNote), s.generated_at ? srcLineFor(doc, 'spend') : null,
    two.length ? table([{ label: '', cell: (r) => r.label }].concat(two.map((w) => ({ label: STRINGS.spendWeekHead(weekWhich(w.week, refMs), weekStart(w.week)), num: true,
      cell: (r) => cell(w, r.k) + (r.k === 'tests' && w.points !== null ? STRINGS.spendPoints(w.points.toFixed(1)) : '') }))), rows) : null,
    share ? h('p', null, STRINGS.spendNoUse(Math.round(share.share * 100) + '%', usd(share.noUse), usd(share.total), share.top.map(([name, cost]) => name + ' (' + usd(cost) + ')').join(' and ')),
      ' ', navLink(hashFor('summary'), STRINGS.spendUsefulnessLink)) : null,
    spendTotalLine(s),
    h('details', { class: 'history' }, h('summary', null, STRINGS.spendAllWeeks),
      table([
        { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => dayOf(w.week, refMs) },
        { label: STRINGS.colEvalRuns, num: true, sort: (w) => w.eval_runs, cell: (w) => (w.eval_runs === null ? STRINGS.noValue : fmtCount(w.eval_runs)) },
        { label: STRINGS.colMeter, num: true, sort: (w) => w.plan_meter_points, cell: (w) => (w.plan_meter_points === null ? STRINGS.noValue : w.plan_meter_points.toFixed(1)) },
        { label: STRINGS.colRunsUsd, num: true, sort: (w) => w.run_usd, cell: (w) => (typeof w.run_usd === 'number' ? usd(w.run_usd) : STRINGS.noValue) },
        { label: STRINGS.colThreads, num: true, sort: (w) => w.thread_spend_usd, cell: (w) => usd(w.thread_spend_usd) },
        { label: STRINGS.colApi, num: true, sort: (w) => w.api_usd, cell: (w) => usd(w.api_usd) }
      ], s.weeks))];
}

const KIND_ROUTE = { check: 'hooks', skill: 'skills', section: 'guidance' };

/* The agent_made block as rows: one per kind with its counts, and the
   agent-made items newest first. Null when the document has none. */
export function agentMadeRows(doc) {
  const a = doc && doc.agent_made;
  if (!a || !a.summary || !Array.isArray(a.items)) return null;
  const kinds = ['check', 'skill', 'section'].filter((k) => a.summary[k]).map((k) => {
    const s = a.summary[k];
    const verdicts = Object.keys(s.agent_verdicts || {}).filter((v) => v !== 'none').sort()
      .map((v) => v + ' ' + s.agent_verdicts[v]).join(', ');
    const use = k === 'check' ? STRINGS.agentMadeImpact.check(fmtCount(s.agent_runs || 0), fmtCount(s.agent_blocked || 0))
      : k === 'skill' ? STRINGS.agentMadeImpact.skill(fmtCount(s.agent_invocations || 0)) : '';
    return { kind: k, total: s.total, agent: s.by_origin.agent, loop: s.by_origin.loop, person: s.by_origin.person,
      afterRule: s.agent_under_rule, impact: [use, STRINGS.agentMadeVerdicts(verdicts)].filter(Boolean).join('; ') };
  });
  const items = a.items.filter((i) => i && i.origin === 'agent')
    .sort((x, y) => (x.created < y.created ? 1 : x.created > y.created ? -1 : (x.id < y.id ? -1 : 1)));
  return { since: a.rule_since, kinds, items };
}

function itemImpact(i) {
  const m = i.impact || {};
  const use = i.kind === 'check' ? STRINGS.agentMadeImpact.check(fmtCount(m.runs || 0), fmtCount(m.blocked || 0))
    : i.kind === 'skill' ? STRINGS.agentMadeImpact.skill(fmtCount(m.invocations || 0)) : '';
  return [use, m.verdict ? clean(m.verdict) : null].filter(Boolean).join('; ') || STRINGS.noValue;
}

function agentMadeView(doc, refMs) {
  const r = agentMadeRows(doc);
  if (!r) return null;
  return [h('p', { class: 'note' }, STRINGS.agentMadeNote(r.since ? fmtUtcDay(parseTime(r.since), refMs) : STRINGS.unknown)),
    table([
      { label: STRINGS.colKind, sort: (k) => k.kind, cell: (k) => STRINGS.agentMadeKinds[k.kind] },
      { label: STRINGS.colTotal, num: true, sort: (k) => k.total, cell: (k) => fmtCount(k.total) },
      { label: STRINGS.colByAgents, num: true, sort: (k) => k.agent, cell: (k) => fmtCount(k.agent) },
      { label: STRINGS.colAfterRule, num: true, sort: (k) => k.afterRule, cell: (k) => fmtCount(k.afterRule) },
      { label: STRINGS.colByLoop, num: true, sort: (k) => k.loop, cell: (k) => fmtCount(k.loop) },
      { label: STRINGS.colByPeople, num: true, sort: (k) => k.person, cell: (k) => fmtCount(k.person) },
      { label: STRINGS.colAgentImpact, sort: (k) => k.impact, cell: (k) => k.impact }
    ], r.kinds),
    r.items.length ? table([
      { label: STRINGS.colKind, sort: (i) => i.kind, cell: (i) => STRINGS.agentMadeKind[i.kind] },
      { label: STRINGS.colName, sort: (i) => i.id, cell: (i) => navLink(hashFor(KIND_ROUTE[i.kind], i.id), clean(i.id)) },
      { label: STRINGS.colMade, sort: (i) => i.created, cell: (i) => fmtUtcDay(parseTime(i.created), refMs) },
      { label: STRINGS.colAfterRule, sort: (i) => (i.under_rule ? 1 : 0), cell: (i) => (i.under_rule ? '✓' : '') },
      { label: STRINGS.colImpact, sort: (i) => itemImpact(i), cell: (i) => itemImpact(i) }
    ], r.items, { tall: true }) : null];
}

export function impactView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const ext = ctx && ctx.ext;
  const covers = (k) => !!(ext && ext.covers && ext.covers(k));
  return h('div', null,
    rangeLine(doc),
    panel(STRINGS.impactSpend, spendView(doc, refMs)),
    covers('cost') ? ext.cost(ctx) : null,
    panel(STRINGS.agentMade, agentMadeView(doc, refMs)),
    panel(STRINGS.impactUseWeeks, hookWeeksView(doc, refMs)),
    // The private usage table covers both lists, private repos included.
    covers('use') ? ext.impactUse(ctx) : [panel(STRINGS.impactUseChecks, checkUseView(doc)), panel(STRINGS.impactUseSkills, skillUseView(doc, refMs))]);
}
