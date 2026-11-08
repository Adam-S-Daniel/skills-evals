/* Building into decisive (Adam, 2026-11-08): how well runs that are still
   "building" (counting toward a keep-or-remove decision that has not happened
   yet) turn into "decisive" runs. Built from each subject's `run_utility`,
   `confidence`, `status` and `decisions`; see utility.js for the rows. */
import { STRINGS } from '../core/strings.js';
import { P } from './strings.js';
import { fmtCount } from '../core/format.js';
import { h } from '../core/h.js';
import { legend } from '../core/charts.js';
import { table } from '../views/bits.js';
import { DATA_REPO } from '../config.js';
import { UTILITY_CLASSES, UTILITY_COLORS } from '../views/utility.js';

/* A subject's distance to a verdict: m = max(helps, no_help) confidence. */
export const NEAR = 0.65;
export const PARTWAY = 0.3;
/* A rough share of each group's building runs expected to end up decisive.
   An estimate made 2026-11-07, not a measurement. */
export const EXPECTED_YIELD = { near: 0.7, partway: 0.3, far: 0.1, never: 0 };
/* The deep-before-wide planner change, merged 2026-11-08 02:53 UTC. */
export const PLANNER_CHANGE = { day: '2026-11-08', pr: 842, url: 'https://github.com/' + DATA_REPO + '/pull/842' };
export const GROUPS = ['near', 'partway', 'far', 'never'];

const DAY_MS = 86400000;
const isDay = (d) => typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d);
const blank = () => ({ runs: 0, cost: 0, unknown: 0 });
const SEGMENTS = ['decided', 'building', 'stranded', 'after'];
const SEGMENT_CLASS = { decisive: 'decided', decisive_superseded: 'decided', building: 'building', stranded: 'stranded', after_decision: 'after' };
const SEGMENT_COLOR = { decided: UTILITY_COLORS.decisive, building: UTILITY_COLORS.building, stranded: UTILITY_COLORS.stranded, after: UTILITY_COLORS.after_decision };

function subjects(doc) {
  const skills = Array.isArray(doc.skills) ? doc.skills : [];
  const sections = doc.guidance && Array.isArray(doc.guidance.sections) ? doc.guidance.sections : [];
  return skills.concat(sections).filter(Boolean);
}

/* The group a subject's building runs belong to, by its current state. */
function groupOf(s) {
  if (s.status === 'skipped') return 'never';
  const c = s.confidence || {};
  const m = Math.max(Number(c.helps) || 0, Number(c.no_help) || 0);
  return m >= NEAR ? 'near' : m >= PARTWAY ? 'partway' : 'far';
}

/* Everything the panel shows, from the whole document. Dollars and expected
   runs are kept at full precision; the view rounds. */
export function conversionTotals(doc) {
  const sum = { decided: blank(), building: blank(), stranded: blank(), after: blank() };
  const byDay = {};
  const decisionDays = {};
  const groups = {};
  GROUPS.forEach((g) => { groups[g] = { subjects: 0, runs: 0, cost: 0, expected: 0 }; });
  const planner = { before: { total: 0 }, since: { total: 0 } };
  GROUPS.forEach((g) => { planner.before[g] = 0; planner.since[g] = 0; });
  for (const s of subjects(doc)) {
    const g = groupOf(s);
    let hasBuilding = false;
    for (const r of Array.isArray(s.run_utility) ? s.run_utility : []) {
      if (!r || !Number.isInteger(r.runs) || r.runs <= 0 || !UTILITY_CLASSES.includes(r.class)) continue;
      const seg = SEGMENT_CLASS[r.class];
      if (!seg) continue;
      const t = sum[seg];
      t.runs += r.runs;
      if (typeof r.cost_usd === 'number' && isFinite(r.cost_usd)) t.cost += r.cost_usd;
      t.unknown += Number.isInteger(r.cost_unknown) ? r.cost_unknown : 0;
      if (seg === 'building') {
        hasBuilding = true;
        groups[g].runs += r.runs;
        if (typeof r.cost_usd === 'number' && isFinite(r.cost_usd)) groups[g].cost += r.cost_usd;
      }
      if (isDay(r.date)) {
        const d = byDay[r.date] = byDay[r.date] || { date: r.date, decided: 0, building: 0, stranded: 0, after: 0 };
        d[seg] += r.runs;
        const side = r.date < PLANNER_CHANGE.day ? planner.before : planner.since;
        side[g] += r.runs;
        side.total += r.runs;
      }
    }
    if (hasBuilding) groups[g].subjects += 1;
    for (const d of Array.isArray(s.decisions) ? s.decisions : []) {
      if (d && isDay(d.decided)) decisionDays[d.decided] = (decisionDays[d.decided] || 0) + 1;
    }
  }
  const groupsTotal = { subjects: 0, runs: 0, cost: 0, expected: 0 };
  for (const g of GROUPS) {
    groups[g].expected = groups[g].runs * EXPECTED_YIELD[g];
    for (const k of Object.keys(groupsTotal)) groupsTotal[k] += groups[g][k];
  }
  const resolved = { runs: sum.decided.runs + sum.stranded.runs, cost: sum.decided.cost + sum.stranded.cost,
    unknown: sum.decided.unknown + sum.stranded.unknown };
  // Every day from the first to the last, so a day without runs shows as a gap.
  const keys = Object.keys(byDay).sort();
  const days = [];
  if (keys.length) {
    const end = Date.parse(keys[keys.length - 1] + 'T00:00:00Z');
    for (let t = Date.parse(keys[0] + 'T00:00:00Z'); t <= end; t += DAY_MS) {
      const k = new Date(t).toISOString().slice(0, 10);
      days.push(byDay[k] || { date: k, decided: 0, building: 0, stranded: 0, after: 0 });
    }
  }
  return {
    decided: sum.decided, building: sum.building, stranded: sum.stranded, after: sum.after, resolved,
    conversion: resolved.runs > 0 ? sum.decided.runs / resolved.runs : null,
    strandedPerDecided: sum.decided.runs > 0 ? sum.stranded.runs / sum.decided.runs : null,
    days,
    decisionsByDay: Object.keys(decisionDays).sort().map((date) => ({ date, cells: decisionDays[date] })),
    groups, groupsTotal, planner
  };
}

const usd = (x) => '$' + x.toFixed(2);
const money = (t) => usd(t.cost) + (t.unknown ? STRINGS.utilityUnknownCost(t.unknown) : '');
const pct = (p, t) => Math.round((p / t) * 100) + '%';

/* 100%-stacked bars, one per run day, with a dashed line where the planner
   changed. */
function shareChart(days) {
  if (!days.length) return null;
  const W = 480, H = 132, L = 36, R = 474, T = 10, B = 108;
  const step = (R - L) / days.length;
  const bw = Math.max(2, Math.min(18, step - 3));
  const lab = { 'font-size': 11, fill: 'var(--muted)' };
  const kids = [
    h('line', { x1: L, x2: R, y1: B, y2: B, stroke: 'var(--axis)', 'stroke-width': 1 }),
    h('text', Object.assign({ x: L - 4, y: T + 4, 'text-anchor': 'end' }, lab), '100%'),
    h('text', Object.assign({ x: L - 4, y: B, 'text-anchor': 'end' }, lab), '0')
  ];
  days.forEach((d, i) => {
    const cx = L + step * i + step / 2;
    const total = SEGMENTS.reduce((s, k) => s + d[k], 0);
    if (total) {
      let y = B;
      for (const k of SEGMENTS) {
        if (!d[k]) continue;
        const hgt = (d[k] / total) * (B - T);
        kids.push(h('rect', { x: (cx - bw / 2).toFixed(1), y: (y - hgt).toFixed(1), width: bw, height: Math.max(0.5, hgt - 1).toFixed(1),
          fill: SEGMENT_COLOR[k], 'data-group': k, 'pointer-events': 'none' }));
        y -= hgt;
      }
    }
    const tip = total ? P.conversionTip(d.date, fmtCount(total), SEGMENTS.filter((k) => d[k])
      .map((k) => P.conversionLegend[k].toLowerCase() + ' ' + pct(d[k], total)).join(', ')) : d.date + ': 0 runs';
    kids.push(h('rect', { x: (cx - step / 2).toFixed(1), y: T, width: step.toFixed(1), height: B - T, fill: 'transparent', class: 'mark', tabindex: 0, 'data-tip': tip }));
    if (days.length <= 8 || i === 0 || i === days.length - 1) {
      kids.push(h('text', Object.assign({ x: cx.toFixed(1), y: B + 17, 'text-anchor': 'middle' }, lab), d.date.slice(5)));
    }
  });
  const at = days.findIndex((d) => d.date === PLANNER_CHANGE.day);
  if (at >= 0) {
    const x = (L + step * at).toFixed(1);
    kids.push(h('line', { x1: x, x2: x, y1: T, y2: B, stroke: 'var(--muted)', 'stroke-width': 1, 'stroke-dasharray': '3 3', 'pointer-events': 'none' }));
    kids.push(h('text', Object.assign({ x: (Number(x) + 3).toFixed(1), y: T + 8, 'text-anchor': 'start' }, lab), '#' + PLANNER_CHANGE.pr));
  }
  return h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart weeks', role: 'img', 'aria-label': P.conversionChartAria(days.length) }, kids);
}

function plannerShares(side) {
  return GROUPS.filter((g) => g !== 'never' || side.never).map((g) => P.conversionPlannerShare(pct(side[g], side.total), P.conversionPlannerWords[g])).join(', ');
}

/* The panel body, or null when no subject carries a ledger. */
export function conversionView(doc) {
  const t = conversionTotals(doc);
  if (!t.decided.runs && !t.building.runs && !t.stranded.runs && !t.after.runs) return null;
  const lead = t.conversion === null
    ? P.conversionLeadNone(fmtCount(t.building.runs), money(t.building))
    : P.conversionLead(fmtCount(t.resolved.runs), fmtCount(t.decided.runs), Math.round(t.conversion * 100) + '%', fmtCount(t.stranded.runs),
      t.strandedPerDecided === null ? '-' : t.strandedPerDecided.toFixed(1), fmtCount(t.building.runs), money(t.building));
  const cols = [
    { label: P.conversionColDistance, cell: (r) => r.label },
    { label: P.conversionColSubjects, num: true, sort: (r) => r.v.subjects, cell: (r) => fmtCount(r.v.subjects) },
    { label: P.conversionColBuilding, num: true, sort: (r) => r.v.runs, cell: (r) => fmtCount(r.v.runs) + ' · ' + usd(r.v.cost) },
    { label: P.conversionColExpected, num: true, sort: (r) => r.v.expected, cell: (r) => '~' + Math.round(r.v.expected) }
  ];
  const rows = GROUPS.map((g) => ({ label: P.conversionGroups[g], v: t.groups[g] })).concat([{ label: P.conversionTotal, v: t.groupsTotal }]);
  const p = t.planner;
  const plannerLink = h('a', { href: PLANNER_CHANGE.url, rel: 'noopener', target: '_blank' }, DATA_REPO.split('/')[1] + '#' + PLANNER_CHANGE.pr);
  const plannerLine = p.since.total
    ? h('p', { class: 'meta' }, P.conversionPlannerLead, plannerLink, P.conversionPlannerSince(fmtCount(p.since.total), plannerShares(p.since)),
      p.before.total ? P.conversionPlannerBefore(fmtCount(p.before.total), plannerShares(p.before)) : null)
    : h('p', { class: 'meta' }, P.conversionPlannerNone, plannerLink, P.conversionPlannerNoneEnd);
  return h('div', { class: 'conversion' },
    h('p', { class: 'meta' }, lead),
    legend(SEGMENTS.map((k) => ({ label: P.conversionLegend[k], color: SEGMENT_COLOR[k] }))),
    shareChart(t.days),
    h('p', { class: 'meta' }, P.conversionCaption),
    t.decisionsByDay.length ? h('p', { class: 'meta' }, P.conversionDecisionsByDay(t.decisionsByDay.map((d) => d.date.slice(5) + ' ' + d.cells).join(', '))) : null,
    table(cols, rows),
    h('p', { class: 'meta' }, P.conversionNote),
    plannerLine);
}
