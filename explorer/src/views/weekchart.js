/* Paired weekly columns (for example local and CI blocks), oldest week on
   the left, hand-drawn like the other charts. */
import { h } from '../core/h.js';
import { fmtCount } from '../core/format.js';
import { legend, chartTitle } from '../core/charts.js';

/* weeks: [{label, a, b}] oldest first; names: [aName, bName]. */
export function weekChart(weeks, names, aria, title, defs) {
  if (!weeks.length || !weeks.some((w) => (w.a || 0) + (w.b || 0) > 0)) return null;
  // Between the phone and desktop widths it shows at, so labels stay readable at both.
  const W = 480, H = 142, L = 36, R = 474, T = 10, B = 118;
  const top = Math.max(1, ...weeks.map((w) => Math.max(w.a || 0, w.b || 0)));
  const step = (R - L) / weeks.length;
  const bw = Math.max(2, Math.min(18, step / 2 - 3));
  const y = (v) => B - (v / top) * (B - T);
  const lab = { 'font-size': 11, fill: 'var(--muted)' };
  const kids = [
    h('line', { x1: L, x2: R, y1: B, y2: B, stroke: 'var(--axis)', 'stroke-width': 1 }),
    h('text', Object.assign({ x: L - 4, y: T + 4, 'text-anchor': 'end' }, lab), fmtCount(top)),
    h('text', Object.assign({ x: L - 4, y: B, 'text-anchor': 'end' }, lab), '0')
  ];
  weeks.forEach((w, i) => {
    const cx = L + step * i + step / 2;
    const pair = [[w.a || 0, 'var(--s1)', -bw - 1], [w.b || 0, 'var(--s2)', 1]];
    for (const [v, color, dx] of pair) {
      if (v > 0) kids.push(h('rect', { x: (cx + dx).toFixed(1), y: y(v).toFixed(1), width: bw, height: (B - y(v)).toFixed(1), rx: 2, fill: color, 'pointer-events': 'none' }));
    }
    kids.push(h('rect', { x: (cx - step / 2).toFixed(1), y: T, width: step.toFixed(1), height: B - T, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': w.label + ': ' + names[0] + ' ' + fmtCount(w.a || 0) + ', ' + names[1] + ' ' + fmtCount(w.b || 0) }));
    if (weeks.length <= 8 || i === 0 || i === weeks.length - 1) {
      kids.push(h('text', Object.assign({ x: cx.toFixed(1), y: B + 17, 'text-anchor': 'middle' }, lab), w.short || w.label));
    }
  });
  return h('div', null, chartTitle(title || aria), legend([{ label: names[0], color: 'var(--s1)', def: defs && defs[0] }, { label: names[1], color: 'var(--s2)', def: defs && defs[1] }]),
    h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart weeks', role: 'img', 'aria-label': aria }, kids));
}
