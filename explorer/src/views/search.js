/* One search across subjects, pull requests and issues, with filters for
   registry, verdict, model and stakes (subjects only). */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel } from '../core/format.js';
import { h, link } from '../core/h.js';
import { chip } from '../core/charts.js';
import { skillItems, sectionItems } from '../core/items.js';
import { hookItems } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { table, navLink, badge } from './bits.js';

const stakesOf = (raw) => (raw && raw.stakes && (raw.stakes.level === 'high' || raw.stakes.level === 'none') ? raw.stakes.level : 'normal');
const modelsOf = (pooled) => pooled.models.filter((m) => m.n > 0 || m.nAbl > 0).map((m) => m.model);

/* Every searchable thing in the document, plus `extra` from the private build. */
export function searchItems(doc, extra) {
  const out = [];
  for (const s of skillItems(doc)) {
    out.push({ kind: 'skill', title: s.name, href: hashFor('skills', s.name), text: [s.name, s.raw.description].join(' '),
      registry: s.raw.registry || null, verdict: s.chip, models: modelsOf(s.pooled), stakes: stakesOf(s.raw), subject: true, priv: s.raw.private === true });
  }
  for (const s of sectionItems(doc, 'next')) {
    out.push({ kind: 'section', title: s.raw.heading || s.id, href: hashFor('guidance', s.id), text: [s.id, s.raw.heading].join(' '),
      registry: null, verdict: s.chip, models: modelsOf(s.pooled), stakes: stakesOf(s.raw), subject: true });
  }
  for (const c of hookItems(doc)) {
    out.push({ kind: 'check', title: c.name, href: hashFor('hooks', c.name), text: [c.name, c.repo].join(' '),
      registry: null, verdict: c.verdict ? 'hook:' + c.verdict : null, models: [], stakes: null, subject: true });
  }
  const a = doc.activity;
  for (const p of a && Array.isArray(a.pulls) ? a.pulls : []) {
    if (p) out.push({ kind: 'pr', title: p.title || '#' + p.number, url: p.url, text: [p.title, p.repo, '#' + p.number].join(' '), detail: String(p.repo || '').split('/').pop() + ' #' + p.number });
  }
  for (const i of a && Array.isArray(a.issues) ? a.issues : []) {
    if (i) out.push({ kind: 'issue', title: i.title || '#' + i.number, url: i.url, text: [i.title, i.repo, '#' + i.number].join(' '), detail: String(i.repo || '').split('/').pop() + ' #' + i.number });
  }
  // One result per destination: a pull request in both the document and a
  // private dataset shows once, the document's copy first.
  const seen = new Set();
  return out.concat(Array.isArray(extra) ? extra : []).filter((it) => {
    const k = it.href || it.url || it.kind + ':' + it.title;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

export function filterItems(items, q) {
  const words = String(q.text || '').toLowerCase().split(/\s+/).filter(Boolean);
  const any = q.registry || q.verdict || q.model || q.stakes;
  return items.filter((it) => {
    if (any && !it.subject) return false;
    if (q.registry && it.registry !== q.registry) return false;
    if (q.verdict && it.verdict !== q.verdict) return false;
    if (q.model && !(it.models || []).includes(q.model)) return false;
    if (q.stakes && it.stakes !== q.stakes) return false;
    const hay = String(it.text || '').toLowerCase();
    return words.every((w) => hay.includes(w));
  });
}

const verdictLabel = (v) => (v && v.startsWith('hook:') ? STRINGS.hookVerdicts[v.slice(5)] || v.slice(5) : STRINGS.chips[v] || v);

function select(label, key, values, current, onFilter, show) {
  return h('label', { class: 'filter' }, label + ' ',
    h('select', { onchange: (e) => onFilter(key, e.currentTarget.value) },
      h('option', { value: '' }, STRINGS.filterAny),
      values.map((v) => h('option', current === v ? { value: v, selected: '' } : { value: v }, show ? show(v) : v))));
}

export function searchView(doc, q, ctx) {
  const items = searchItems(doc, ctx && ctx.ext && ctx.ext.searchExtra ? ctx.ext.searchExtra(ctx) : null);
  const uniq = (f) => Array.from(new Set(items.flatMap((it) => [].concat(f(it) || [])))).filter(Boolean).sort();
  const on = (ctx && ctx.onFilter) || (() => {});
  const hits = filterItems(items, q).slice(0, 300);
  return h('section', { class: 'block search' },
    h('h2', null, STRINGS.searchHeading(clean(q.text || ''))),
    h('div', { class: 'filters' },
      select(STRINGS.filterRegistry, 'registry', uniq((it) => it.registry), q.registry, on, clean),
      select(STRINGS.filterVerdict, 'verdict', uniq((it) => it.verdict), q.verdict, on, verdictLabel),
      select(STRINGS.filterModel, 'model', uniq((it) => it.models), q.model, on, friendlyModel),
      select(STRINGS.filterStakes, 'stakes', uniq((it) => it.stakes), q.stakes, on, (v) => STRINGS.stakesWords[v] || v),
      h('button', { type: 'button', class: 'linkish', onclick: ctx && ctx.onClear ? ctx.onClear : null }, STRINGS.searchClear)),
    hits.length ? table([
      { label: STRINGS.colKind, sort: (it) => it.kind, cell: (it) => STRINGS.kinds[it.kind] },
      { label: STRINGS.colWhat, sort: (it) => it.title, cell: (it) => [it.href ? navLink(it.href, clean(it.title)) : link(it.url, clean(it.title)) || clean(it.title),
        it.priv ? [' ', badge(STRINGS.privateBadge, 'private')] : null] },
      { label: STRINGS.colDetail, sort: (it) => it.verdict || it.detail || '', cell: (it) => (it.verdict && !it.verdict.startsWith('hook:') ? chip(it.verdict)
        : it.verdict ? verdictLabel(it.verdict) : clean(it.detail || '')) }
    ], hits, { tall: true }) : h('p', null, STRINGS.searchNone));
}
