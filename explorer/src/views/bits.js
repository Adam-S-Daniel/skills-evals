/* Small shared pieces: sortable tables, tiles, source lines, internal links. */
import { STRINGS } from '../core/strings.js';
import { fmtDateTime, parseTime } from '../core/format.js';
import { h, findAll } from '../core/h.js';

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
    spend: d.spend && d.spend.generated_at, usage: d.usage && d.usage.to, coverage: d.coverage && d.coverage.as_of }[which];
  const ms = parseTime(at);
  return isFinite(ms) ? ms : parseTime(d.generated_at);
}
export const BLOCKS = ['doc', 'activity', 'queue', 'spend', 'usage', 'coverage'];
export function srcLineFor(doc, which, source) { return srcLine(source || STRINGS.srcDoc, blockMs(doc, which)); }

/* The page's one line: the document's time when every block was read at
   once, else the oldest and newest read. */
export function rangeLine(doc) {
  const times = BLOCKS.map((k) => blockMs(doc, k)).filter((m) => isFinite(m));
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

/* A scrolling table is a labeled region: one the table did not name itself
   takes the heading of the panel or fold that holds it. */
function nameTables(kids, title) {
  for (const k of [].concat(kids).flat(Infinity)) {
    findAll(k, (n) => n.attrs && n.attrs['data-auto-label'] === '').forEach((n) => {
      n.attrs['data-region'] = title;
      n.attrs['data-auto-label'] = null;
    });
  }
}

/* A section with a heading, or null when it has nothing to show, so an empty
   panel hides itself. */
export function panel(title, kids, attrs) {
  const list = (Array.isArray(kids) ? kids : [kids]).filter((k) => k !== null && k !== undefined && k !== false);
  if (!list.length) return null;
  nameTables(list, title);
  return h('section', Object.assign({ class: 'block' }, attrs || {}), h('h2', null, title), list);
}

/* A closed fold with a heading, or null when it has nothing to show. */
export function fold(title, kids) {
  const list = (Array.isArray(kids) ? kids : [kids]).filter((k) => k !== null && k !== undefined && k !== false);
  if (list.length) nameTables(list, title);
  return list.length ? h('details', { class: 'block history' }, h('summary', null, title), list) : null;
}

function cellValue(td) {
  const raw = td.getAttribute('data-sort');
  return raw === null ? td.textContent : raw;
}

/* Rows a table shows before "Show all <n>". Every table taller than this is
   capped, so a page of hundreds of rows opens as a short one. */
export const ROW_CAP = 50;
/* A table with more rows than this gets a "Skip table" button before it, so
   a keyboard reader is not made to tab through every link in it. */
export const SKIP_OVER = 5;
/* Above this many columns a phone shows each row as a stacked block. */
export const STACK_OVER = 3;

/* Hide every counted row past the first `cap` unless `open`. `rows` are the
   table body's rows as { hidden, filtered }; a filtered row (hidden by the
   "Problems only" switch) is not counted. Returns how many rows are counted. */
export function applyCap(rows, cap, open) {
  let counted = 0;
  for (const r of rows) {
    if (r.filtered) { r.hidden = false; continue; }
    counted += 1;
    r.hidden = !open && counted > cap;
  }
  return counted;
}

/* Re-apply the cap to the rows on the page, after a sort or the switch. */
export function refreshCap(wrap) {
  const body = wrap.querySelector('tbody');
  const cap = Number(wrap.getAttribute('data-cap'));
  if (!body || !(cap > 0)) return;
  const only = !!wrap.closest('.problems-only');
  const rows = Array.from(body.children).map((tr) => ({ el: tr, filtered: only && tr.hasAttribute('data-ok'), hidden: false }));
  const counted = applyCap(rows, cap, wrap.getAttribute('data-open') === 'true');
  rows.forEach((r) => { if (r.el.hidden !== r.hidden) r.el.hidden = r.hidden; });
  const btn = wrap.querySelector('button.show-all');
  if (btn) {
    btn.hidden = counted <= cap;
    btn.textContent = wrap.getAttribute('data-open') === 'true' ? STRINGS.showFewer(cap) : STRINGS.showAll(counted);
  }
  markScroller(wrap);
}

/* A table wrapper is a focusable, labeled region only while it actually
   scrolls (a table that fits is not a tab stop). The label was set on the
   wrapper as `data-region` when the table was built. */
export function markScroller(wrap) {
  const scrolls = wrap.scrollWidth > wrap.clientWidth + 1 || wrap.scrollHeight > wrap.clientHeight + 1;
  if (scrolls) {
    wrap.setAttribute('role', 'region');
    wrap.setAttribute('tabindex', '0');
    wrap.setAttribute('aria-label', wrap.getAttribute('data-region') || '');
  } else {
    wrap.removeAttribute('role');
    wrap.removeAttribute('tabindex');
    wrap.removeAttribute('aria-label');
  }
}
export function markScrollers(root) {
  root.querySelectorAll('.tablewrap').forEach(markScroller);
}

/* Where "Skip table" sends the keyboard: the Show all button while it is
   showing, else the next heading after the table (made focusable on the
   spot). Null when the page has neither. */
export function skipTarget(wrap) {
  const btn = wrap.querySelector('button.show-all');
  if (btn && !btn.hidden) return btn;
  for (let n = wrap; n; n = n.parentElement) {
    for (let s = n.nextElementSibling; s; s = s.nextElementSibling) {
      const hd = /^H[1-6]$/.test(s.tagName) ? s : (s.querySelector ? s.querySelector('h1,h2,h3,h4') : null);
      if (hd) return hd;
    }
  }
  return wrap.querySelector('.table-end');
}

/* Clicking a heading sorts the rows already on the page, so a sort needs no
   re-render and keeps the reader's place. Enter or Space on a focused heading
   does the same. */
export function sorter(index) {
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
    const wrap = tableEl.closest ? tableEl.closest('.tablewrap') : null;
    if (wrap) refreshCap(wrap);
  };
}

/* cols: [{label, num, sort(row), cell(row)}]. A column's `sort` gives the
   value it sorts by (a number or a string), so a formatted cell still sorts
   by what it means. Every cell carries its column's label as `data-label`,
   which a phone prints above the value when it stacks the row.
   opts: tall, cls, rowAttrs(row), foot, cap (rows shown first; tall tables
   default to ROW_CAP), counts(row) (does a row count toward the cap when the
   page opens), scroll (keep the sideways scroll on a phone, with a hint, for a
   table of numbers that must stay in columns), label (the region's name; a
   panel fills it from its heading). */
export function table(cols, rows, opts) {
  const o = opts || {};
  const cap = o.cap || (o.tall ? ROW_CAP : 0);
  const head = h('tr', null, cols.map((c, i) => h('th', { class: c.num ? 'num' : null, scope: 'col', tabindex: 0,
    'aria-sort': 'none', title: STRINGS.sortHint, onclick: sorter(i), onkeydown: sorter(i) }, c.label)));
  const counted = rows.filter((r) => !o.counts || o.counts(r));
  const shown = new Set(cap ? counted.slice(0, cap) : counted);
  const body = rows.map((r) => {
    const hide = cap > 0 && (!o.counts || o.counts(r)) && !shown.has(r);
    const extra = o.rowAttrs ? o.rowAttrs(r) : null;
    return h('tr', hide ? Object.assign({ hidden: true }, extra || {}) : extra, cols.map((c) => {
      const v = c.sort ? c.sort(r) : null;
      return h('td', { class: [c.num ? 'num' : null, c.cls || null].filter(Boolean).join(' ') || null, 'data-label': c.label,
        'data-sort': v === null || v === undefined ? null : String(v) }, c.cell(r));
    }));
  });
  const more = cap > 0 && rows.length > cap;
  const visible = cap > 0 ? Math.min(counted.length, cap) : counted.length;
  const wrap = h('div', { class: 'tablewrap' + (o.tall ? ' tall' : ''), 'data-auto-label': o.label ? null : '',
    'data-region': o.label || STRINGS.tableLabel(cols.map((c) => c.label).filter(Boolean).join(', ')), 'data-cap': cap > 0 ? cap : null },
  o.scroll ? h('p', { class: 'scroll-hint' }, STRINGS.scrollHint) : null,
  visible > SKIP_OVER ? h('button', { type: 'button', class: 'skip-table', onclick: (e) => {
    const to = skipTarget(e.currentTarget.closest('.tablewrap'));
    if (!to) return;
    if (!to.hasAttribute('tabindex') && !/^(BUTTON|A|INPUT)$/.test(to.tagName)) to.setAttribute('tabindex', '-1');
    to.focus();
  } }, STRINGS.skipTable) : null,
  h('table', { class: [o.cls || null, cols.length > STACK_OVER && !o.scroll ? 'stack' : null].filter(Boolean).join(' ') || null }, h('thead', null, head), h('tbody', null, body),
    o.foot && o.foot.length ? h('tfoot', null, o.foot.map((r) => h('tr', null, cols.map((c) => h('td', { class: c.num ? 'num' : null, 'data-label': c.label }, c.cell(r)))))) : null),
  more ? h('button', { type: 'button', class: 'linkish show-all', hidden: counted.length <= cap ? true : null, onclick: (e) => {
    const w = e.currentTarget.closest('.tablewrap');
    w.setAttribute('data-open', w.getAttribute('data-open') === 'true' ? 'false' : 'true');
    refreshCap(w);
  } }, STRINGS.showAll(counted.length)) : null,
  visible > SKIP_OVER ? h('span', { class: 'table-end', tabindex: -1 }) : null);
  return wrap;
}
