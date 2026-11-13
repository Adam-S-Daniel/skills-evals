/* The gain range chart and the "How close is a decision?" panel. */
import { pts } from '../core/rules.js';
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel } from '../core/format.js';
import { h } from '../core/h.js';
import { chartTitle } from '../core/charts.js';

/* Runs still needed to move a level from `conf` to `level`, assuming the
   evidence (-ln(1 - level)) grows in step with the pair count. Returns
   { node, projected }: `projected` is true for a line that projects a pace. */
export function estimateLine(which, conf, level, pairs, cap) {
  const line = (text) => h('p', { class: 'meta', 'data-est': which }, text);
  if (typeof level !== 'number') return { node: null, projected: false };
  if (conf >= level) return { node: line(STRINGS.confReached(which)), projected: false };
  if (!Number.isInteger(pairs) || pairs <= 0) return { node: null, projected: false };
  if (conf <= 0) return { node: line(STRINGS.confNoMove(which)), projected: false };
  const more = Math.max(1, Math.ceil(pairs * (-Math.log(1 - level)) / (-Math.log(1 - conf))) - pairs);
  if (Number.isInteger(cap) && cap > 0 && pairs + more > cap)
    return { node: line(STRINGS.confPastCap(which, cap)), projected: true };
  return { node: line(STRINGS.confMore(which, more)), projected: true };
}

/* A name cut to `n` characters, the last one an ellipsis. */
export function clipName(text, n) {
  const t = String(text);
  return t.length > n ? t.slice(0, n - 1) + '…' : t;
}

/* Signed whole points with a real minus sign: +22, 0, −18. */
export function signedPoints(x) {
  const n = Math.round(x);
  return n > 0 ? '+' + n : n < 0 ? '−' + (-n) : '0';
}

/* The gain range chart's geometry: the label column, the axis from -100
   to +100 points, and the runs meter on the right. */
export const RANGE = { W: 340, AX0: 116, AX1: 282, MX: 292, MW: 42, TOP: 16, ROW: 32, TASK_CHARS: 19 };
export const rangeX = (v) => RANGE.AX0 + ((Math.max(-100, Math.min(100, v)) + 100) / 200) * (RANGE.AX1 - RANGE.AX0);
export const RANGE_COLORS = { keeps: 'var(--good)', 'removes-ready': 'var(--s2)', 'no-room': 'var(--axis)', paused: 'var(--axis)', open: 'var(--s1)' };

/* rows: confidence.cells, each {model, task, pairs, gain, low, high, votes, status}. */
export function rangeChart(rows, margin, cap) {
  const fin = (x) => typeof x === 'number' && isFinite(x);
  rows = rows.filter((r) => r && fin(r.gain) && fin(r.low) && fin(r.high));
  if (!rows.length) return null;
  const { W, AX0, AX1, MX, MW, TOP, ROW } = RANGE;
  const H = TOP + rows.length * ROW + 18;
  const bottom = TOP + rows.length * ROW;
  const lab = { 'font-size': 10, fill: 'var(--muted)' };
  const kids = [];
  for (const v of [-100, -50, 0, 50, 100]) {
    const x = rangeX(v);
    if (v !== 0) kids.push(h('line', { x1: x, x2: x, y1: TOP - 2, y2: bottom, stroke: 'var(--grid)', 'stroke-width': 1 }));
    kids.push(h('text', { ...lab, x: x, y: H - 3, 'text-anchor': 'middle', 'data-axis': v }, signedPoints(v)));
  }
  kids.push(h('line', { x1: rangeX(0), x2: rangeX(0), y1: TOP - 2, y2: bottom, stroke: 'var(--axis)', 'stroke-width': 1.5, 'data-line': 'zero' }));
  if (margin !== null) {
    const mx = rangeX(margin);
    kids.push(h('line', { x1: mx, x2: mx, y1: TOP - 2, y2: bottom, stroke: 'var(--muted)', 'stroke-width': 1, 'stroke-dasharray': '3 3', 'data-line': 'margin' }));
    kids.push(h('text', { ...lab, x: mx, y: TOP - 5, 'text-anchor': 'middle' }, '+' + margin));
  }
  kids.push(h('text', { ...lab, x: 0, y: H - 3 }, STRINGS.rangeAxis));
  kids.push(h('text', { ...lab, x: MX, y: TOP - 5 }, STRINGS.rangeRuns));
  rows.forEach((r, i) => {
    const y = TOP + i * ROW;
    const model = friendlyModel(r.model);
    const task = typeof r.task === 'string' && r.task ? clean(r.task) : null;
    kids.push(h('text', { x: 0, y: y + 12, 'font-size': 11, fill: 'var(--ink-2)' }, model));
    if (task) kids.push(h('text', { x: 0, y: y + 25, 'font-size': 10, fill: 'var(--muted)', 'data-tip': task }, clipName(task, RANGE.TASK_CHARS)));
    const x0 = rangeX(Math.min(r.low, r.high)), x1 = rangeX(Math.max(r.low, r.high));
    const width = Math.max(2, x1 - x0);
    const color = RANGE_COLORS[r.status] || RANGE_COLORS.open;
    kids.push(h('rect', { class: 'range-bar', x: x0.toFixed(2), y: y + 10, width: width.toFixed(2), height: 10,
      rx: Math.min(5, width / 2).toFixed(2), fill: color, 'fill-opacity': r.status === 'open' || !RANGE_COLORS[r.status] ? 0.55 : 1,
      'data-status': r.status, 'pointer-events': 'none' }));
    kids.push(h('circle', { class: 'gain-dot', cx: rangeX(r.gain).toFixed(2), cy: y + 15, r: 4, fill: 'var(--ink)',
      stroke: 'var(--surface)', 'stroke-width': 1.5, 'pointer-events': 'none' }));
    const pairs = Number.isInteger(r.pairs) ? r.pairs : 0;
    kids.push(h('text', { x: MX, y: y + 12, 'font-size': 11, fill: 'var(--ink)', class: 'runs' }, cap ? pairs + '/' + cap : String(pairs)));
    if (cap) {
      kids.push(h('rect', { x: MX, y: y + 17, width: MW, height: 4, rx: 2, fill: 'var(--base)' }));
      const fw = MW * Math.min(1, pairs / cap);
      if (fw > 0) kids.push(h('rect', { class: 'runs-fill', x: MX, y: y + 17, width: fw.toFixed(2), height: 4, rx: 2, fill: 'var(--ink-2)' }));
      kids.push(h('line', { x1: MX + MW, x2: MX + MW, y1: y + 15, y2: y + 23, stroke: 'var(--ink)', 'stroke-width': 1 }));
    }
    kids.push(h('rect', { x: AX0 - 4, y: y + 4, width: AX1 - AX0 + 8, height: 22, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip-pos': 'below',
      'data-tip': STRINGS.rangeTip(model, task, signedPoints(r.gain), signedPoints(r.low), signedPoints(r.high),
        STRINGS.rangeTipRuns(pairs, cap), r.votes !== false) }));
  });
  return h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart range', role: 'img',
    'aria-label': STRINGS.rangeAria(rows.length, margin) }, kids);
}

/* The decision rules the policy sets, shared by a subject's page. Every
   figure comes from the data (evals/gate-policy.yml); an absent one is null
   and shown as unknown, never a built-in number (docs/rules.md). */
function policyFigures(policy) {
  const ok = (x) => typeof x === 'number' && isFinite(x);
  return {
    margin: policy && ok(policy.objective_margin) ? pts(policy.objective_margin) : null,
    keep: policy && ok(policy.benefit_confidence) ? policy.benefit_confidence : null,
    remove: policy && ok(policy.retire_confidence) ? policy.retire_confidence : null,
    versions: policy && Number.isInteger(policy.min_cli_versions) && policy.min_cli_versions > 0 ? policy.min_cli_versions : null,
    cap: policy && Number.isInteger(policy.max_runs_per_cell) && policy.max_runs_per_cell > 0 ? policy.max_runs_per_cell : null
  };
}

const whole = (x) => (x === null ? STRINGS.unknown : Math.round(x * 100) + '%');

export function confidenceView(c, policy, subject) {
  const ok = (x) => typeof x === 'number' && isFinite(x);
  if (!c || !ok(c.helps)) return h('p', { class: 'meta' }, STRINGS.confidenceNone);
  const { margin, keep, remove, versions, cap } = policyFigures(policy);
  const kids = [h('p', { class: 'conf-h' }, STRINGS.confHeading)];
  const chart = Array.isArray(c.cells) && c.cells.length ? rangeChart(c.cells, margin, cap) : null;
  if (chart) {
    kids.push(chartTitle(STRINGS.rangeTitle), chart);
  }
  if (chart) {
    kids.push(h('p', { class: 'meta' }, STRINGS.rangeWhat));
    kids.push(h('p', { class: 'meta' }, STRINGS.rangeRule(margin)));
    kids.push(h('p', { class: 'meta' }, STRINGS.rangeLevels(whole(keep), whole(remove), subject, versions)));
  }
  const keepEst = estimateLine(STRINGS.confKeepWord, c.helps, keep, c.keep_pairs, cap);
  kids.push(keepEst.node);
  let removeEst = { node: null, projected: false };
  if (c.no_help === null) kids.push(h('p', { class: 'meta' }, STRINGS.confNoRoom(margin)));
  else if (ok(c.no_help)) {
    removeEst = estimateLine(STRINGS.confRemoveWord, c.no_help, remove, c.no_help_pairs, cap);
    kids.push(removeEst.node);
  }
  if (cap && Number.isInteger(c.max_pairs)) kids.push(h('p', { class: 'meta' }, STRINGS.confRuns(c.max_pairs, cap)));
  else if (cap) kids.push(h('p', { class: 'meta' }, STRINGS.confidenceCap(cap)));
  if ((keepEst.projected || removeEst.projected)) kids.push(h('p', { class: 'meta' }, STRINGS.confPace));
  return h('div', { class: 'conf' }, kids);
}
