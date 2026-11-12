/* Paired weekly columns (for example local and CI blocks), oldest week on
   the left, hand-drawn like the other charts. */
import { h } from '../core/h.js';
import { STRINGS } from '../core/strings.js';
import { fmtCount } from '../core/format.js';
import { legend, chartTitle } from '../core/charts.js';

/* One bar far above the rest would flatten every other week to nothing. When
   the tallest value is more than twice the second tallest (of at least three
   non-zero values), the axis stops at the second tallest and the tall bar is
   drawn cut off and labeled with its real count. {top, cut: {i, v, k}|null}. */
export function weekScale(weeks) {
  const vals = [];
  weeks.forEach((w, i) => [[w.a, 0], [w.b, 1]].forEach(([v, k]) => { if (v > 0) vals.push({ v, i, k }); }));
  vals.sort((x, y) => y.v - x.v);
  if (vals.length >= 3 && vals[0].v > 2 * vals[1].v) return { top: vals[1].v, cut: vals[0] };
  return { top: Math.max(1, vals.length ? vals[0].v : 1), cut: null };
}

/* weeks: [{label, a, b}] oldest first; names: [aName, bName]. */
export function weekChart(weeks, names, aria, title, defs) {
  if (!weeks.length || !weeks.some((w) => (w.a || 0) + (w.b || 0) > 0)) return null;
  // Between the phone and desktop widths it shows at, so labels stay readable at both.
  const W = 480, H = 142, L = 36, R = 474, T = 10, B = 118;
  const { top, cut } = weekScale(weeks);
  const step = (R - L) / weeks.length;
  const bw = Math.max(2, Math.min(18, step / 2 - 3));
  const y = (v) => B - (Math.min(v, top) / top) * (B - T);
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
      if (cut && cut.v === v && cut.i === i) {
        // The break: a slanted gap across the bar, and its real count above it.
        const bx = cx + dx, by = y(v) + 14;
        kids.push(h('polygon', { points: bx + ',' + (by + 3) + ' ' + (bx + bw) + ',' + (by - 3) + ' ' + (bx + bw) + ',' + (by + 1) + ' ' + bx + ',' + (by + 7), fill: 'var(--surface)', 'pointer-events': 'none' }));
        kids.push(h('text', Object.assign({ x: (bx + bw / 2).toFixed(1), y: T - 1, 'text-anchor': 'middle' }, lab), fmtCount(v)));
      }
    }
    kids.push(h('rect', { x: (cx - step / 2).toFixed(1), y: T, width: step.toFixed(1), height: B - T, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': w.label + ': ' + names[0] + ' ' + fmtCount(w.a || 0) + ', ' + names[1] + ' ' + fmtCount(w.b || 0) }));
    if (weeks.length <= 8 || i === 0 || i === weeks.length - 1) {
      kids.push(h('text', Object.assign({ x: cx.toFixed(1), y: B + 17, 'text-anchor': 'middle' }, lab), w.short || w.label));
    }
  });
  const note = cut ? h('p', { class: 'note' }, STRINGS.weekCut(weeks[cut.i].label, fmtCount(cut.v), names[cut.k], fmtCount(top))) : null;
  return h('div', null, chartTitle(title || aria), legend([{ label: names[0], color: 'var(--s1)', def: defs && defs[0] }, { label: names[1], color: 'var(--s2)', def: defs && defs[1] }]),
    h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'chart weeks', role: 'img', 'aria-label': aria }, kids), note);
}
