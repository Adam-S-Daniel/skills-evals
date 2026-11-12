/* Run usefulness (Adam, 2026-11-07): which runs helped decide a subject's
   keep-or-remove and which bought nothing, over a chosen period. The rows are
   each subject's `run_utility` (harness/gates.py, RUN UTILITY): runs and
   list-price cost per UTC day, model, class and discard reason. */
import { STRINGS } from '../core/strings.js';
import { clean, fmtCount, fmtUsd } from '../core/format.js';
import { h, toDom } from '../core/h.js';
import { legend, chartTitle } from '../core/charts.js';
import { term } from '../core/terms.js';
import { table } from './bits.js';

/* The classes in the order they are drawn, and their colors. "No use" is
   after_decision + stranded + discarded. */
export const UTILITY_CLASSES = ['decisive', 'decisive_superseded', 'building', 'after_decision', 'stranded', 'discarded'];
export const NO_USE = ['after_decision', 'stranded', 'discarded'];
export const UTILITY_COLORS = { decisive: 'var(--good)', decisive_superseded: 'color-mix(in srgb, var(--good) 45%, var(--surface))', building: 'var(--s1)',
  after_decision: 'var(--warning)', stranded: 'var(--s2)', discarded: 'var(--axis)' };
export const PERIODS = [{ key: '7', days: 7 }, { key: '30', days: 30 }, { key: 'all', days: null }];
export const DEFAULT_PERIOD = '30';

const DAY_MS = 86400000;
const isDay = (d) => typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d);

/* The first UTC day a period covers, counting the reference day itself, or
   null for all time (or no reference). */
export function periodStart(period, refMs) {
  const p = PERIODS.find((x) => x.key === period);
  if (!p || p.days === null || !isFinite(refMs)) return null;
  return new Date(refMs - (p.days - 1) * DAY_MS).toISOString().slice(0, 10);
}

/* Rows inside a period: on or after its first day. A row without a day
   counts only toward all time. */
export function inPeriod(rows, period, refMs) {
  const from = periodStart(period, refMs);
  const list = Array.isArray(rows) ? rows.filter((r) => r && Number.isInteger(r.runs) && r.runs > 0 && UTILITY_CLASSES.includes(r.class)) : [];
  return from === null ? list : list.filter((r) => isDay(r.date) && r.date >= from);
}

const blank = () => ({ runs: 0, cost: 0, unknown: 0 });
function add(t, r) {
  t.runs += r.runs;
  if (typeof r.cost_usd === 'number' && isFinite(r.cost_usd)) t.cost += r.cost_usd;
  t.unknown += Number.isInteger(r.cost_unknown) ? r.cost_unknown : 0;
}

/* {classes: {class: {runs, cost, unknown}}, noUse, useful, total, reasons:
   {slug: {runs, cost, unknown}}, days: [{date, class: runs}]} of the rows in
   a period. Dollars are summed at full precision and rounded only on show. */
export function utilityTotals(rows, period, refMs) {
  const out = { classes: {}, noUse: blank(), total: blank(), reasons: {}, days: [] };
  UTILITY_CLASSES.forEach((c) => { out.classes[c] = blank(); });
  const days = {};
  for (const r of inPeriod(rows, period, refMs)) {
    add(out.classes[r.class], r);
    add(out.total, r);
    if (NO_USE.includes(r.class)) add(out.noUse, r);
    if (typeof r.reason === 'string' && r.reason) add(out.reasons[r.reason] = out.reasons[r.reason] || blank(), r);
    if (isDay(r.date)) {
      const d = days[r.date] = days[r.date] || { date: r.date };
      d[r.class] = (d[r.class] || 0) + r.runs;
    }
  }
  // Every day from the first to the last, so a day without runs shows as a gap.
  const keys = Object.keys(days).sort();
  for (let t = keys.length ? Date.parse(keys[0] + 'T00:00:00Z') : 0; keys.length && t <= Date.parse(keys[keys.length - 1] + 'T00:00:00Z'); t += DAY_MS) {
    const k = new Date(t).toISOString().slice(0, 10);
    out.days.push(days[k] || { date: k });
  }
  return out;
}

const usd = (x) => fmtUsd(x);
const money = (t) => usd(t.cost) + (t.unknown ? STRINGS.utilityUnknownCost(t.unknown) : '');

/* Per-day stacked columns of runs by class, oldest day on the left. */
export function dayChart(days) {
  if (!days.length) return null;
  const W = 480, H = 132, L = 36, R = 474, T = 10, B = 108;
  const tops = days.map((d) => UTILITY_CLASSES.reduce((s, c) => s + (d[c] || 0), 0));
  const top = Math.max(1, ...tops);
  const step = (R - L) / days.length;
  const bw = Math.max(2, Math.min(18, step - 3));
  const lab = { 'font-size': 11, fill: 'var(--muted)' };
  const kids = [
    h('line', { x1: L, x2: R, y1: B, y2: B, stroke: 'var(--axis)', 'stroke-width': 1 }),
    h('text', Object.assign({ x: L - 4, y: T + 4, 'text-anchor': 'end' }, lab), fmtCount(top)),
    h('text', Object.assign({ x: L - 4, y: B, 'text-anchor': 'end' }, lab), '0')
  ];
  days.forEach((d, i) => {
    const cx = L + step * i + step / 2;
    let y = B;
    for (const c of UTILITY_CLASSES) {
      const v = d[c] || 0;
      if (!v) continue;
      const hgt = (v / top) * (B - T);
      // A 1px surface gap between stacked segments keeps them apart.
      kids.push(h('rect', { x: (cx - bw / 2).toFixed(1), y: (y - hgt).toFixed(1), width: bw, height: Math.max(0.5, hgt - 1).toFixed(1),
        fill: UTILITY_COLORS[c], 'data-class': c, 'pointer-events': 'none' }));
      y -= hgt;
    }
    kids.push(h('rect', { x: (cx - step / 2).toFixed(1), y: T, width: step.toFixed(1), height: B - T, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': d.date + ': ' + UTILITY_CLASSES.filter((c) => d[c]).map((c) => STRINGS.utilityClasses[c] + ' ' + fmtCount(d[c])).join(', ') }));
    if (days.length <= 8 || i === 0 || i === days.length - 1) {
      kids.push(h('text', Object.assign({ x: cx.toFixed(1), y: B + 17, 'text-anchor': 'middle' }, lab), d.date.slice(5)));
    }
  });
  return h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart weeks', role: 'img', 'aria-label': STRINGS.utilityChartAria(days.length) }, kids);
}

/* The last 30 days' share of test dollars that bought nothing, and the two
   biggest causes by dollars: { share, noUse, total, top: [[reason, cost]] }, or
   null when no run in the period has a known cost. Dollars at full precision. */
export function noUseShare(doc, refMs) {
  const t = utilityTotals(fleetGroups(doc)[0].rows, DEFAULT_PERIOD, refMs);
  if (!(t.total.cost > 0)) return null;
  const top = Object.entries(t.reasons).filter(([, v]) => v.cost > 0).sort((a, b) => b[1].cost - a[1].cost || (a[0] < b[0] ? -1 : 1)).slice(0, 2)
    .map(([k, v]) => [reasonName(k), v.cost]);
  return { share: t.noUse.cost / t.total.cost, noUse: t.noUse.cost, total: t.total.cost, top };
}

const reasonName = (k) => (Object.prototype.hasOwnProperty.call(STRINGS.discardedReasons, k) ? STRINGS.discardedReasons[k] : clean(k));

/* The body for one period: the classes' runs and cost, the reasons, and the
   per-day chart. `groups` is [{label, rows}]: one for a subject, several
   (all, skills, guidance) for the fleet. */
export function utilityBody(groups, period, refMs) {
  const totals = groups.map((g) => ({ label: g.label, t: utilityTotals(g.rows, period, refMs) }));
  const main = totals[0].t;
  if (!main.total.runs) return h('div', { class: 'utility-body' }, h('p', { class: 'note' }, STRINGS.utilityNone));
  const cell = (t) => fmtCount(t.runs) + ' · ' + money(t);
  const cols = [{ label: STRINGS.utilityColClass, cell: (r) => h('span', null, h('span', { class: 'sw', style: 'background:' + (UTILITY_COLORS[r.key] || 'transparent') }), ' ', STRINGS.utilityDefs[r.key] ? term(r.label, STRINGS.utilityDefs[r.key]) : r.label) }]
    .concat(totals.map((g, i) => ({ label: g.label, num: true, sort: (r) => r.values[i].runs, cell: (r) => cell(r.values[i]) })));
  const rows = UTILITY_CLASSES.map((c) => ({ key: c, label: STRINGS.utilityClasses[c], values: totals.map((g) => g.t.classes[c]) }))
    .filter((r) => r.values.some((v) => v.runs))
    .concat([{ key: 'no-use', label: STRINGS.utilityNoUse, values: totals.map((g) => g.t.noUse) },
      { key: 'total', label: STRINGS.utilityTotal, values: totals.map((g) => g.t.total) }]);
  const reasons = Object.entries(main.reasons).sort((a, b) => b[1].runs - a[1].runs || (a[0] < b[0] ? -1 : 1));
  return h('div', { class: 'utility-body' },
    h('p', { class: 'meta' }, STRINGS.utilityLead(fmtCount(main.noUse.runs), usd(main.noUse.cost), fmtCount(main.total.runs), usd(main.total.cost))),
    table(cols, rows),
    reasons.length ? h('p', { class: 'meta' }, STRINGS.utilityReasons(reasons.map(([k, t]) => reasonName(k) + ' ' + fmtCount(t.runs) + ' (' + usd(t.cost) + ')').join(', '))) : null,
    main.days.length ? [chartTitle(STRINGS.dayTitle), legend(UTILITY_CLASSES.filter((c) => main.classes[c].runs).map((c) => ({ label: STRINGS.utilityClasses[c], color: UTILITY_COLORS[c], def: STRINGS.utilityDefs[c] }))),
      dayChart(main.days)] : null);
}

/* The period buttons and the body; a press re-renders the body in place, so
   the rest of the page keeps its state. */
export function utilityView(groups, refMs, period) {
  let current = period || DEFAULT_PERIOD;
  const buttons = PERIODS.map((p) => h('button', { type: 'button', 'data-period': p.key, 'aria-pressed': p.key === current ? 'true' : 'false',
    onclick: (e) => {
      current = p.key;
      const root = e.currentTarget.closest('.utility');
      root.querySelectorAll('button[data-period]').forEach((b) => b.setAttribute('aria-pressed', b.getAttribute('data-period') === current ? 'true' : 'false'));
      const old = root.querySelector('.utility-body');
      old.replaceWith(toDom(utilityBody(groups, current, refMs), e.currentTarget.ownerDocument));
    } }, STRINGS.utilityPeriods[p.key]));
  return h('div', { class: 'utility' },
    h('div', { class: 'seg', role: 'group', 'aria-label': STRINGS.utilityPeriodLabel }, buttons),
    h('p', { class: 'meta' }, STRINGS.utilityWhat),
    utilityBody(groups, current, refMs));
}

/* A subject's cell versions as lines: "Sonnet on task-a: v1 decided
   benefit on 2026-11-02 (runs 10-28 to 11-02); v2 building since 11-05". */
export function decisionsView(decisions, friendly) {
  const list = Array.isArray(decisions) ? decisions.filter((d) => d && typeof d.model === 'string') : [];
  if (!list.length) return null;
  const cells = {};
  for (const d of list) {
    const k = (d.pair || '') + '|' + (d.fixture || '') + '|' + d.model;
    (cells[k] = cells[k] || []).push(d);
  }
  const items = Object.keys(cells).sort().map((k) => {
    const vs = cells[k].sort((a, b) => ((a.from || '') < (b.from || '') ? -1 : (a.from || '') > (b.from || '') ? 1 : a.current - b.current));
    const head = vs[0];
    const name = friendly(head.model) + (head.fixture ? STRINGS.utilityOn(clean(head.fixture)) : '') + (head.pair === 'alone' ? STRINGS.utilityAlone : '');
    // An old version that never decided was stranded by the change.
    const parts = vs.map((d, i) => STRINGS.utilityVersion(i + 1, d.current,
      !d.current && !d.decided ? STRINGS.utilityStrandedVersion : STRINGS.utilityDecision(d.class), d.decided, d.from, d.to));
    return h('li', null, name + ': ' + parts.join('; '));
  });
  return [h('p', { class: 'meta' }, STRINGS.utilityVersionsLead), h('ul', { class: 'plain' }, items)];
}

/* Every listed subject's rows, for the fleet view. */
export function fleetGroups(doc) {
  const skills = (Array.isArray(doc.skills) ? doc.skills : []).flatMap((s) => (s && Array.isArray(s.run_utility) ? s.run_utility : []));
  const sections = (doc.guidance && Array.isArray(doc.guidance.sections) ? doc.guidance.sections : [])
    .flatMap((s) => (s && Array.isArray(s.run_utility) ? s.run_utility : []));
  return [{ label: STRINGS.utilityAll, rows: skills.concat(sections) }, { label: STRINGS.utilitySkills, rows: skills },
    { label: STRINGS.utilityGuidance, rows: sections }];
}

/* True when any listed subject carries a ledger. */
export function hasUtility(doc) {
  return fleetGroups(doc)[0].rows.length > 0;
}
