/* The weekly trend line on each card. */
import { STRINGS } from '../core/strings.js';
import { fmtDay, fmtGain } from '../core/format.js';
import { h } from '../core/h.js';
import { chartTitle } from '../core/charts.js';

/* compact: on a list card, where the reading guide carries the caption. */
export function trendChart(points, refMs, compact, kind) {
  if (!points.length) return h('p', { class: 'trend-cap' }, STRINGS.trendNone);
  if (points.length === 1) {
    const p = points[0];
    return h('p', { class: 'trend-cap' }, STRINGS.trendOne(fmtDay(p.start + 1000, refMs), fmtGain(p.gain)));
  }
  const W = 300, H = 124, XL = 34, XR = 292, YT = 10, YB = 102;
  const m = Math.max(...points.map((p) => Math.abs(p.gain * 100)));
  const top = Math.max(5, Math.ceil(m / 5) * 5);
  const oldest = points[0], newest = points[points.length - 1];
  const wOld = oldest.week, wNew = newest.week;
  const x = (w) => (wOld === wNew ? XR : XL + ((wOld - w) / (wOld - wNew)) * (XR - XL));
  const y = (g) => YT + ((top - g * 100) / (2 * top)) * (YB - YT);
  const yMid = y(0);
  const lab = { 'font-size': 11, fill: 'var(--muted)' };
  const kids = [
    h('line', { x1: XL, x2: XR, y1: YT, y2: YT, stroke: 'var(--grid)', 'stroke-dasharray': '3 3', 'stroke-width': 1 }),
    h('line', { x1: XL, x2: XR, y1: YB, y2: YB, stroke: 'var(--grid)', 'stroke-dasharray': '3 3', 'stroke-width': 1 }),
    h('line', { x1: XL, x2: XR, y1: yMid, y2: yMid, stroke: 'var(--axis)', 'stroke-width': 1 }),
    h('text', { ...lab, x: 28, y: YT, 'text-anchor': 'end', 'dominant-baseline': 'middle' }, '+' + top),
    h('text', { ...lab, x: 28, y: yMid, 'text-anchor': 'end', 'dominant-baseline': 'middle' }, '0'),
    h('text', { ...lab, x: 28, y: YB, 'text-anchor': 'end', 'dominant-baseline': 'middle' }, '\u2212' + top),
    h('text', { ...lab, x: XL, y: 118, 'text-anchor': 'start' }, fmtDay(oldest.start + 1000, refMs)),
    h('text', { ...lab, x: XR, y: 118, 'text-anchor': 'end' }, fmtDay(newest.start + 1000, refMs)),
    h('polyline', { points: points.map((p) => x(p.week).toFixed(1) + ',' + y(p.gain).toFixed(1)).join(' '),
      fill: 'none', stroke: 'var(--s1)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' })
  ];
  points.forEach((p, i) => {
    const last = i === points.length - 1;
    const cx = x(p.week).toFixed(1), cy = y(p.gain).toFixed(1);
    kids.push(h('circle', { cx, cy, r: last ? 4.5 : 3.5, fill: 'var(--s1)', stroke: 'var(--surface)', 'stroke-width': 1.5,
      'pointer-events': 'none' }));
    kids.push(h('circle', { cx, cy, r: 10, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': STRINGS.trendTip(fmtDay(p.start + 1000, refMs), fmtGain(p.gain)), 'data-tip-pos': 'below' }));
  });
  return h('div', null, chartTitle(STRINGS.trendTitle[kind] || STRINGS.trendTitle.skills),
    h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'spark', role: 'img', 'aria-label': STRINGS.trendCaption }, kids),
    compact ? null : h('p', { class: 'trend-cap' }, STRINGS.trendCaption));
}
