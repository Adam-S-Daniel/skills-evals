/* One route's content for one document: the six groups (five in the public
   build), the subject lists and the subject pages. */
import { STRINGS } from '../core/strings.js';
import { parseTime } from '../core/format.js';
import { h } from '../core/h.js';
import { skillItems, sectionItems, wholeGuidance } from '../core/items.js';
import { groupOf, GROUPS, hashFor } from '../core/route.js';
import { DEFAULT_DATA_URL } from '../adapters/web.js';
import { wholeView } from './whole.js';
import { skillCard, sectionCard, chipSummary } from './cards.js';
import { coverageView } from './coverage.js';
import { alertsView } from './alerts.js';
import { summaryView } from './summary.js';
import { hooksList, hookPage } from './hooks.js';
import { subjectPage } from './subject.js';
import { loopView } from './loop.js';
import { impactView } from './impact.js';
import { opsView } from './ops.js';
import { methodView, removedPage } from './method.js';
import { searchView } from './search.js';
import { navLink, srcLine } from './bits.js';

/* The Skills or the Guidance list: every card, the coverage and that kind's
   alerts. */
export function buildPage(doc, mode, opts) {
  const o = opts || {};
  const refMs = parseTime(doc.generated_at);
  if (mode === 'guidance') {
    const items = sectionItems(doc, o.sortBy);
    const hd = o.handlers || {};
    return h('div', null,
      srcLine(STRINGS.srcDoc, refMs),
      wholeView(wholeGuidance(doc), refMs),
      h('section', null, h('h2', null, STRINGS.sectionsHeading), h('p', { class: 'note' }, STRINGS.sectionsNote),
        chipSummary(items, mode),
        h('div', { class: 'toolbar' }, h('span', { class: 'note' }, STRINGS.sortLabel),
          h('div', { class: 'seg', role: 'group', 'aria-label': STRINGS.sortLabel },
            h('button', { type: 'button', 'aria-pressed': o.sortBy !== 'size' && o.sortBy !== 'value' ? 'true' : 'false', onclick: hd.sortNext || null }, STRINGS.sortNext),
            h('button', { type: 'button', 'aria-pressed': o.sortBy === 'value' ? 'true' : 'false', onclick: hd.sortValue || null }, STRINGS.sortValue),
            h('button', { type: 'button', 'aria-pressed': o.sortBy === 'size' ? 'true' : 'false', onclick: hd.sortSize || null }, STRINGS.sortSize))),
        items.length ? h('div', { class: 'cards' }, items.map((it) => sectionCard(it, refMs, doc))) : h('p', null, STRINGS.noCards)),
      coverageView(doc, mode), alertsView(doc, mode));
  }
  const items = skillItems(doc);
  const u = doc.usage;
  return h('div', null,
    srcLine(STRINGS.srcDoc, refMs),
    h('section', null, h('h2', null, STRINGS.skillsHeading), h('p', { class: 'note' }, STRINGS.skillsNote),
      u && typeof u.sessions_scanned === 'number' ? h('p', { class: 'note' }, STRINGS.usageNote(u.sessions_scanned.toLocaleString('en-US'))) : null,
      chipSummary(items, mode),
      items.length ? h('div', { class: 'cards' }, items.map((it) => skillCard(it, refMs, doc))) : h('p', null, STRINGS.noCards)),
    coverageView(doc, mode), alertsView(doc, mode));
}

function subNav(current) {
  return h('nav', { class: 'subnav', 'aria-label': STRINGS.subNavLabel }, GROUPS.hooks.map((name) =>
    navLink(hashFor(name), STRINGS.subTabs[name], { id: 'sub-' + name, 'aria-current': name === current ? 'page' : null })));
}

function isSearching(q) {
  return !!(q && (q.text || q.registry || q.verdict || q.model || q.stakes));
}

/* opts: { sortBy, handlers, url, ext, search, onFilter, onClear }. `ext` is
   the private build's overlays; the public build passes none. */
export function renderRoute(doc, route, opts) {
  const o = opts || {};
  const ctx = { doc, route, url: o.url || DEFAULT_DATA_URL, ext: o.ext || null, onFilter: o.onFilter, onClear: o.onClear };
  if (isSearching(o.search)) return h('div', null, searchView(doc, o.search, ctx));
  const group = groupOf(route.name);
  let body;
  switch (route.name) {
    case 'needs': body = ctx.ext && ctx.ext.needs ? ctx.ext.needs(ctx) : null; break;
    case 'hooks': body = route.id ? hookPage(doc, route.id, ctx) : hooksList(doc); break;
    case 'skills': body = route.id ? subjectPage(doc, 'skills', route.id, ctx) : buildPage(doc, 'skills', o); break;
    case 'guidance': body = route.id ? subjectPage(doc, 'guidance', route.id, ctx) : buildPage(doc, 'guidance', o); break;
    case 'removed': body = removedPage(doc); break;
    case 'method': body = methodView(doc, ctx); break;
    case 'loop': body = loopView(doc, ctx); break;
    case 'impact': body = impactView(doc, ctx); break;
    case 'ops': body = opsView(doc, ctx); break;
    default: body = summaryView(doc, ctx);
  }
  return h('div', null,
    h('h1', { class: 'group-title' }, STRINGS.groups[group]),
    group === 'hooks' ? subNav(route.name) : null,
    o.notice ? h('p', { class: 'panel failure' }, o.notice) : null,
    body);
}
