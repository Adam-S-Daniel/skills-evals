/* "Trending toward removal": the subjects whose recent runs score worse than
   the runs before them. It is the system working as designed, so it is a
   table of its own, one row per subject, not an alert that needs action. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, fmt2, fmtSigned2, roundDecimals } from '../core/format.js';
import { h, link } from '../core/h.js';
import { skillTerm, sectionTerm, fixtureTerm } from '../core/terms.js';
import { table } from './bits.js';

const isNum = (x) => typeof x === 'number' && isFinite(x);

/* One row per subject (kind + name), folding every model and fixture of its
   regression alerts into it. */
export function trendingRows(doc, mode) {
  const by = new Map();
  for (const a of Array.isArray(doc.alerts) ? doc.alerts : []) {
    if (!a || a.kind !== 'regression' || (mode !== 'all' && a.subject !== (mode === 'guidance' ? 'guidance' : 'skill'))) continue;
    const key = a.subject + ':' + a.name;
    if (!by.has(key)) by.set(key, { subject: a.subject, name: String(a.name), models: [], changes: [], urls: [] });
    const row = by.get(key);
    const model = a.model ? friendlyModel(a.model) : null;
    if (model && !row.models.includes(model)) row.models.push(model);
    row.changes.push({ alert: a, model });
    if (typeof a.url === 'string' && !row.urls.includes(a.url)) row.urls.push(a.url);
  }
  return Array.from(by.values()).sort((x, y) => (x.name < y.name ? -1 : x.name > y.name ? 1 : 0));
}

const cap = (nodes) => {
  const first = nodes[0];
  return typeof first === 'string' ? [first.charAt(0).toUpperCase() + first.slice(1)].concat(nodes.slice(1)) : nodes;
};

/* An older document words the change itself ("X lost-delta on F: with minus
   without went from 0.17 to 0.0." or "X regressed: the judge mean fell by
   1.5 (threshold 1.0, noise 0.47)."): read its figures back into fields. */
export function legacyFields(a) {
  const t = String(a.text || '');
  const fixture = /^\S+ (?:lost-delta|regressed) on (\S+?):/.exec(t);
  const adv = /with minus without went from (-?[\d.]+?)\.? to (-?[\d.]+?)\.?$/.exec(t);
  if (adv) return { fixture: fixture ? fixture[1] : null, measure: 'advantage', previous: Number(adv[1]), current: Number(adv[2]) };
  const fell = /the (judge|objective) mean fell by (-?[\d.]+) \(threshold (-?[\d.]+), noise (-?[\d.]+)\)/.exec(t);
  if (fell) return { fixture: fixture ? fixture[1] : null, measure: fell[1], drop: Number(fell[2]), threshold: Number(fell[3]), noise: Number(fell[4]) };
  return {};
}

/* The change as plain English, from the alert's fields when it has them. */
export function changeNodes(alert) {
  const a = alert.measure ? alert : Object.assign({}, alert, legacyFields(alert));
  const noun = STRINGS.trendKindNoun[a.subject] || 'subject';
  const fixture = typeof a.fixture === 'string' && a.fixture ? fixtureTerm(a.fixture) : null;
  let rest;
  if (a.measure === 'advantage' && isNum(a.previous) && isNum(a.current)) {
    rest = STRINGS.trendAdvantage(noun, fmtSigned2(a.previous), fmtSigned2(a.current));
  } else if ((a.measure === 'judge' || a.measure === 'objective') && isNum(a.drop) && isNum(a.threshold) && isNum(a.noise)) {
    rest = STRINGS.trendFell(STRINGS.trendMeasure[a.measure], fmt2(a.drop), fmt2(a.threshold), fmt2(a.noise));
  } else {
    // An older document words the change itself; its numbers are still rounded.
    return [clean(roundDecimals(a.text || ''))];
  }
  return fixture ? [STRINGS.trendOnFixture, fixture, ', ', rest] : cap([rest]);
}

function subjectCell(r) {
  const label = r.subject === 'guidance' ? sectionTerm(r.name) : skillTerm(r.name);
  return h('span', null, label, h('span', { class: 'muted' }, ' · ' + STRINGS.trendingKinds[r.subject]));
}

function issueNumber(url) {
  const m = /\/issues\/(\d+)$/.exec(String(url));
  return m ? m[1] : null;
}

export function trendingView(doc, mode) {
  const rows = trendingRows(doc, mode);
  if (!rows.length) return null;
  const C = STRINGS.trendingCols;
  return h('section', { class: 'block trending' }, h('h2', null, STRINGS.trendingHeading),
    h('p', { class: 'note' }, STRINGS.trendingNote),
    table([
      { label: C.subject, sort: (r) => r.name, cell: subjectCell },
      { label: C.models, sort: (r) => r.models.join(', '), cell: (r) => r.models.join(', ') || STRINGS.noValue },
      { label: C.what, cell: (r) => h('ul', { class: 'plain' }, r.changes.map((c) => h('li', null, cap(changeNodes(c.alert)),
        r.models.length > 1 && c.model ? STRINGS.trendModelSuffix(c.model) : null))) },
      { label: C.details, cell: (r) => r.urls.map((u, i) => [i ? ', ' : null, link(u, STRINGS.trendingIssue(issueNumber(u)))]) }
    ], rows, { cls: 'trending-table' }));
}
