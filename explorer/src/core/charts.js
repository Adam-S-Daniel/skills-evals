/* Chart and label helpers shared by the views. */
import { STRINGS } from './strings.js';
import { fmtCount, fmtRate } from './format.js';
import { h } from './h.js';

export function barPath(x, y, w, hgt, r) {
  // square at the baseline (left), 4px rounded data end (right)
  const rr = Math.min(r, w, hgt / 2);
  if (w <= 0) return '';
  return 'M' + x + ',' + y + 'H' + (x + w - rr) + 'A' + rr + ',' + rr + ' 0 0 1 ' + (x + w) + ',' + (y + rr)
    + 'V' + (y + hgt - rr) + 'A' + rr + ',' + rr + ' 0 0 1 ' + (x + w - rr) + ',' + (y + hgt) + 'H' + x + 'Z';
}

/* rows: [{label, p, t, color}] */
export function barChart(rows, label) {
  const W = 330, L = 112, R = 230, BH = 12, GAP = 8, TOP = 4;
  const H = TOP + rows.length * (BH + GAP) + 2;
  const span = R - L;
  const kids = [];
  kids.push(h('line', { x1: L, x2: L, y1: 0, y2: H - 2, stroke: 'var(--base)', 'stroke-width': 1 }));
  rows.forEach((row, i) => {
    const y = TOP + i * (BH + GAP);
    const rate = row.t > 0 ? row.p / row.t : 0;
    const w = Math.max(0, Math.min(1, rate)) * span;
    const a = fmtCount(row.p), b = fmtCount(row.t);
    kids.push(h('text', { x: 0, y: y + BH - 2, 'font-size': 12, fill: 'var(--ink-2)' }, row.label));
    kids.push(h('rect', { x: L, y: y - 2, width: span, height: BH + 4, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': STRINGS.barTip(row.label, a, b, fmtRate(row.p, row.t)) }));
    if (w > 0) kids.push(h('path', { d: barPath(L, y, w, BH, 4), fill: row.color, 'pointer-events': 'none' }));
    kids.push(h('text', { x: L + w + 4, y: y + BH - 2, 'font-size': 12, fill: 'var(--ink)', 'pointer-events': 'none' }, a + ' of ' + b));
  });
  return h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart', role: 'img', 'aria-label': label }, kids);
}

export function chip(kind, ruleText) {
  const rule = ruleText || STRINGS.chipRules[kind];
  return h('span', { class: 'chip ' + kind, title: STRINGS.chips[kind] + ': ' + rule, tabindex: 0,
    'aria-label': STRINGS.chips[kind] + '. ' + rule },
    h('span', { class: 'ic', 'aria-hidden': 'true' }), STRINGS.chips[kind]);
}

export function legend(items) {
  return h('div', { class: 'legend' }, items.map((it) =>
    h('span', null, h('span', { class: 'sw', style: 'background:' + it.color }), it.label)));
}
