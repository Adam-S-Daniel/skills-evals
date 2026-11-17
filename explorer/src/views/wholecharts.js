/* The whole-guidance comparison taken apart, so a change in WHICH tasks were
   tested is never read as a change in how much the guidance helps: one row
   per section, then week-to-week panels on the tasks both weeks share
   (core/stats.js sectionSpread and weekPairs). */
import { STRINGS } from '../core/strings.js';
import { clean, fmtDay, fmtCount, fmtRate } from '../core/format.js';
import { hashFor } from '../core/route.js';
import { h } from '../core/h.js';
import { chartTitle, legend } from '../core/charts.js';
import { navLink } from './bits.js';

/* The newest week pairs drawn, and the weeks listed under them. */
export const PAIR_CAP = 6;
/* A week is called out when one task took at least this share of its eval runs. */
export const TOP_TASK_SHARE = 1 / 3;

/* Arm labels by kind of comparison: the first is the solid dot, the second the open square. */
const armsOf = (kind) => (kind === 'skills' ? [STRINGS.barWith, STRINGS.barWithout] : kind === 'guidance' ? [STRINGS.barAll, STRINGS.barAblated] : [STRINGS.barWholeFull, STRINGS.barWholeNone]);

const pct = (x) => Math.round(x * 100) + '%';
const weekDay = (w, refMs) => fmtDay(w.start + 1000, refMs);

function spreadRow(r, refMs) {
  const W = 200, H = 16, L = 6, R = 194, Y = 8;
  const x = (rate) => L + Math.max(0, Math.min(1, rate)) * (R - L);
  const xw = x(r.wp / r.wt), xo = x(r.op / r.ot);
  const name = clean(r.heading);
  const kids = [
    h('line', { x1: L, x2: R, y1: Y, y2: Y, stroke: 'var(--grid)', 'stroke-width': 1 }),
    h('line', { x1: x(0.5), x2: x(0.5), y1: 2, y2: H - 2, stroke: 'var(--grid)', 'stroke-width': 1 }),
    h('line', { x1: Math.min(xw, xo), x2: Math.max(xw, xo), y1: Y, y2: Y, stroke: r.gain < 0 ? 'var(--s2)' : 'var(--s1)', 'stroke-width': 3, 'pointer-events': 'none' }),
    // No guidance is the open square, all the guidance the solid dot, so the two stay apart where they land on one spot.
    h('rect', { x: (xo - 4.5).toFixed(1), y: Y - 4.5, width: 9, height: 9, fill: 'var(--surface)', stroke: 'var(--s2)', 'stroke-width': 2, 'pointer-events': 'none' }),
    h('circle', { cx: xw.toFixed(1), cy: Y, r: 3.5, fill: 'var(--s1)', 'pointer-events': 'none' }),
    h('rect', { x: 0, y: 0, width: W, height: H, fill: 'transparent', class: 'mark', tabindex: 0,
      'data-tip': STRINGS.spreadTip(name, fmtCount(r.wp), fmtCount(r.wt), fmtRate(r.wp, r.wt), fmtCount(r.op), fmtCount(r.ot), fmtRate(r.op, r.ot)) })
  ];
  return h('div', { class: 'spread-row' },
    h('span', { class: 'spread-name' }, navLink(hashFor('guidance', r.id), name)),
    h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'spread-track', role: 'img', 'aria-label': STRINGS.spreadAria(name) }, kids),
    h('span', { class: 'spread-nums' }, STRINGS.spreadNums(fmtCount(r.wp), fmtCount(r.wt), fmtCount(r.op), fmtCount(r.ot)),
      h('span', { class: 'sub' }, STRINGS.spreadMeta(r.n, r.tasks, fmtDay(r.last, refMs)))));
}

/* rows: core/stats.js sectionSpread. */
export function sectionSpreadChart(rows, refMs) {
  if (!rows.length) return null;
  const group = (title, note, list) => (list.length ? [h('p', { class: 'spread-group' }, title, note ? h('span', { class: 'sub' }, ' ' + note) : null),
    list.map((r) => spreadRow(r, refMs))] : null);
  const on = rows.filter((r) => r.tested), off = rows.filter((r) => !r.tested);
  return h('div', { class: 'spread-wrap' }, chartTitle(STRINGS.spreadTitle), h('p', { class: 'trend-cap' }, STRINGS.spreadCaption),
    legend([{ label: STRINGS.barWholeFull, color: 'var(--s1)', def: STRINGS.barDefs.all }, { label: STRINGS.barWholeNone, color: 'var(--s2)', def: STRINGS.barDefs.none }]),
    h('div', { class: 'spread' },
      h('div', { class: 'spread-row spread-axis', 'aria-hidden': 'true' }, h('span', null), h('span', { class: 'spread-scale' }, h('span', null, '0%'), h('span', null, '50%'), h('span', null, '100%')), h('span', null)),
      group(STRINGS.spreadOn(on.length), null, on), group(STRINGS.spreadOff(off.length), STRINGS.spreadOffNote, off)));
}

function pairPanel(p, refMs, kind) {
  const kd = STRINGS.pairKinds[kind] || {};
  const [labWith, labWithout] = armsOf(kind);
  const from = weekDay(p.from, refMs), to = weekDay(p.to, refMs);
  const head = h('p', { class: 'pair-head' }, STRINGS.pairHead(from, to));
  const mix = h('p', { class: 'sub' }, STRINGS.pairMix(p.shared, p.dropped, p.added));
  if (!p.shared) return h('div', { class: 'pair' }, head, h('p', { class: 'note' }, STRINGS.pairNone), mix);
  const W = 180, H = 118, XL = 44, XR = 136, YT = 12, YB = 96;
  const y = (rate) => YB - Math.max(0, Math.min(1, rate)) * (YB - YT);
  const lab = { 'font-size': 11, fill: 'var(--muted)' };
  const kids = [
    h('line', { x1: XL, x2: XR, y1: YT, y2: YT, stroke: 'var(--grid)', 'stroke-dasharray': '3 3', 'stroke-width': 1 }),
    h('line', { x1: XL, x2: XR, y1: y(0.5), y2: y(0.5), stroke: 'var(--grid)', 'stroke-dasharray': '3 3', 'stroke-width': 1 }),
    h('line', { x1: XL, x2: XR, y1: YB, y2: YB, stroke: 'var(--axis)', 'stroke-width': 1 }),
    h('text', { ...lab, x: XL, y: H - 6, 'text-anchor': 'middle' }, from),
    h('text', { ...lab, x: XR, y: H - 6, 'text-anchor': 'middle' }, to)
  ];
  // The two value labels on one side are pushed apart when the lines end close together.
  const labelYs = (a, b) => { const ya = y(a), yb = y(b); if (Math.abs(ya - yb) >= 12) return [ya, yb]; const mid = (ya + yb) / 2; return ya <= yb ? [mid - 6, mid + 6] : [mid + 6, mid - 6]; };
  const [twY, toY] = labelYs(p.then.with, p.then.without), [nwY, noY] = labelYs(p.now.with, p.now.without);
  const arms = [
    { key: 'with', label: labWith, color: 'var(--s1)', ys: [twY, nwY], pk: 'wp', tk: 'wt', square: false },
    { key: 'without', label: labWithout, color: 'var(--s2)', ys: [toY, noY], pk: 'op', tk: 'ot', square: true }
  ];
  for (const a of arms) {
    kids.push(h('line', { x1: XL, x2: XR, y1: y(p.then[a.key]).toFixed(1), y2: y(p.now[a.key]).toFixed(1), stroke: a.color, 'stroke-width': 2, 'stroke-linecap': 'round' }));
    [[XL, p.then, p.from, a.ys[0], 'end', -9], [XR, p.now, p.to, a.ys[1], 'start', 9]].forEach(([cx, s, wk, ly, anchor, dx]) => {
      const cy = y(s[a.key]);
      kids.push(a.square
        ? h('rect', { x: cx - 4, y: (cy - 4).toFixed(1), width: 8, height: 8, fill: 'var(--surface)', stroke: a.color, 'stroke-width': 2, 'pointer-events': 'none' })
        : h('circle', { cx, cy: cy.toFixed(1), r: 4, fill: a.color, stroke: 'var(--surface)', 'stroke-width': 1.5, 'pointer-events': 'none' }));
      kids.push(h('text', { x: cx + dx, y: ly.toFixed(1), 'font-size': 11, 'font-weight': 600, fill: a.color, 'text-anchor': anchor, 'dominant-baseline': 'middle', 'pointer-events': 'none' }, pct(s[a.key])));
      kids.push(h('circle', { cx, cy: cy.toFixed(1), r: 10, fill: 'transparent', class: 'mark', tabindex: 0, 'data-tip-pos': 'below',
        'data-tip': STRINGS.pairTip(a.label, weekDay(wk, refMs), pct(s[a.key]), p.shared, fmtCount(s[a.pk]), fmtCount(s[a.tk]), s.n) }));
    });
  }
  return h('div', { class: 'pair' }, head,
    h('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'pair-chart', role: 'img', 'aria-label': STRINGS.pairAria(from, to, pct(p.then.with), pct(p.then.without), pct(p.now.with), pct(p.now.without), ...(kd.arms || [])) }, kids),
    h('p', { class: 'pair-gap' }, STRINGS.pairGap(Math.round((p.then.with - p.then.without) * 100), Math.round((p.now.with - p.now.without) * 100), kd.noun)),
    mix);
}

/* What each week tested: how much, and whether one task took most of it. */
function weekLine(w, refMs, single) {
  const big = w.n > 1 && w.top.n / w.n >= TOP_TASK_SHARE - 1e-9 && w.tasks > 1;
  return h('li', null, single ? STRINGS.weekMixOne(weekDay(w, refMs), w.n, w.tasks) : STRINGS.weekMix(weekDay(w, refMs), w.n, w.tasks, w.sections),
    big ? [' ', h('strong', null, single ? STRINGS.weekTopOne(w.top.n, w.n, clean(w.top.fixture))
      : STRINGS.weekTop(w.top.n, w.n, clean(w.top.heading), clean(w.top.fixture)))] : null);
}

/* weekly: core/stats.js weekPairs; kind: 'whole' (default), 'skills' or 'guidance'. */
export function weekPairsChart(weekly, refMs, kind = 'whole') {
  if (!weekly.weeks.length) return h('p', { class: 'trend-cap' }, STRINGS.trendNone);
  const kd = STRINGS.pairKinds[kind] || { title: STRINGS.pairTitle, caption: STRINGS.pairCaption };
  const weeks = weekly.weeks.slice(-PAIR_CAP).reverse();
  const list = h('ul', { class: 'plain weekmix' }, weeks.map((w) => weekLine(w, refMs, kind !== 'whole')));
  if (!weekly.pairs.length) return h('div', null, chartTitle(kd.title), h('p', { class: 'trend-cap' }, STRINGS.pairOneWeek), list);
  return h('div', null, chartTitle(kd.title), h('p', { class: 'trend-cap' }, kd.caption),
    h('div', { class: 'pairs' }, weekly.pairs.slice(-PAIR_CAP).map((p) => pairPanel(p, refMs, kind))),
    chartTitle(STRINGS.weekMixTitle), list);
}
