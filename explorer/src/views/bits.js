/* Small shared pieces: sortable tables, tiles, source lines, internal links. */
import { STRINGS } from '../core/strings.js';
import { fmtDateTime, parseTime } from '../core/format.js';
import { h } from '../core/h.js';

/* A link to another route of this page. */
export function navLink(hash, text, attrs) {
  return h('a', Object.assign({ href: hash, class: 'nav-link' }, attrs || {}), text);
}

/* The line under a panel heading that says where its numbers come from and
   when they were read, in US Eastern time. */
export function srcLine(source, ms) {
  return h('p', { class: 'src' }, STRINGS.srcLine(source, isFinite(ms) ? fmtDateTime(ms) : ''));
}

/* When each block of the document was read. A panel prints its own block's
   time, never the document's, so no row is newer than the line above it. */
export function blockMs(doc, which) {
  const d = doc || {};
  const at = { doc: d.generated_at, activity: d.activity && d.activity.fetched_at, queue: d.fixture_queue && d.fixture_queue.generated_at,
    spend: d.spend && d.spend.generated_at, usage: d.usage && d.usage.to }[which];
  const ms = parseTime(at);
  return isFinite(ms) ? ms : parseTime(d.generated_at);
}
export function srcLineFor(doc, which, source) { return srcLine(source || STRINGS.srcDoc, blockMs(doc, which)); }

/* The page's one line: the document's time when every block was read at
   once, else the oldest and newest read. */
export function rangeLine(doc) {
  const times = ['doc', 'activity', 'queue', 'spend', 'usage'].map((k) => blockMs(doc, k)).filter((m) => isFinite(m));
  if (!times.length) return srcLine(STRINGS.srcDoc, NaN);
  const lo = Math.min.apply(null, times), hi = Math.max.apply(null, times);
  if (fmtDateTime(lo) === fmtDateTime(hi)) return srcLine(STRINGS.srcDoc, blockMs(doc, 'doc'));
  return h('p', { class: 'src' }, STRINGS.srcRange(fmtDateTime(lo), fmtDateTime(hi)));
}
export function srcTip(source, ms) { return STRINGS.srcTip(source, isFinite(ms) ? fmtDateTime(ms) : ''); }

/* A number that names its source and as-of time on hover. */
export function num(value, source, ms) {
  return h('span', { class: 'n', tabindex: 0, 'data-tip': srcTip(source, ms) }, value);
}

export function badge(text, kind) {
  return h('span', { class: 'badge' + (kind ? ' ' + kind : '') }, text);
}

/* tile({label, value, note, tip, href, small}); `small` for a long value such as a time. */
export function tile(t) {
  // A tile that links stretches its label's link over the whole tile, so the
  // definition buttons inside it stay real buttons, never nested in a link.
  const label = t.href ? h('a', { class: 'tile-label tile-link', href: t.href }, t.label) : h('span', { class: 'tile-label' }, t.label);
  const plain = typeof t.value === 'string';
  const kids = [label,
    h('span', { class: 'tile-num' + (t.small ? ' small' : ''), tabindex: t.tip && plain ? 0 : null, 'data-tip': t.tip && plain ? t.tip : null }, t.value),
    t.note ? h('span', { class: 'tile-note' }, t.note) : null];
  return h('div', { class: 'tile' + (t.href ? ' linked' : '') }, kids);
}

/* A section with a heading, or null when it has nothing to show, so an empty
   panel hides itself. */
export function panel(title, kids, attrs) {
  const list = (Array.isArray(kids) ? kids : [kids]).filter((k) => k !== null && k !== undefined && k !== false);
  if (!list.length) return null;
  return h('section', Object.assign({ class: 'block' }, attrs || {}), h('h2', null, title), list);
}

function cellValue(td) {
  const raw = td.getAttribute('data-sort');
  return raw === null ? td.textContent : raw;
}

/* Clicking a heading sorts the rows already on the page, so a sort needs no
   re-render and keeps the reader's place. */
function sorter(index) {
  return (e) => {
    if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
    if (e.type === 'keydown') e.preventDefault();
    const th = e.currentTarget;
    const tableEl = th.closest('table');
    const tbody = tableEl.querySelector('tbody');
    const dir = th.getAttribute('aria-sort') === 'ascending' ? -1 : 1;
    tableEl.querySelectorAll('th').forEach((x) => x.setAttribute('aria-sort', 'none'));
    th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
    const rows = Array.from(tbody.children);
    rows.sort((a, b) => {
      const x = cellValue(a.children[index]), y = cellValue(b.children[index]);
      const nx = Number(x), ny = Number(y);
      const c = x !== '' && y !== '' && isFinite(nx) && isFinite(ny) ? nx - ny : String(x).localeCompare(String(y));
      return c * dir;
    });
    rows.forEach((r) => tbody.appendChild(r));
  };
}

/* cols: [{label, num, sort(row), cell(row)}]. A column's `sort` gives the
   value it sorts by (a number or a string), so a formatted cell still sorts
   by what it means. */
export function table(cols, rows, opts) {
  const o = opts || {};
  const head = h('tr', null, cols.map((c, i) => h('th', { class: c.num ? 'num' : null, scope: 'col', tabindex: 0,
    'aria-sort': 'none', title: STRINGS.sortHint, onclick: sorter(i), onkeydown: sorter(i) }, c.label)));
  const body = rows.map((r) => h('tr', o.rowAttrs ? o.rowAttrs(r) : null, cols.map((c) => {
    const v = c.sort ? c.sort(r) : null;
    return h('td', { class: [c.num ? 'num' : null, c.cls || null].filter(Boolean).join(' ') || null, 'data-sort': v === null || v === undefined ? null : String(v) }, c.cell(r));
  })));
  return h('div', { class: 'tablewrap' + (o.tall ? ' tall' : '') },
    h('table', { class: o.cls || null }, h('thead', null, head), h('tbody', null, body)));
}
