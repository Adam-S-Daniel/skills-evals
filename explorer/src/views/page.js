/* One route's content for one document: the six groups (five in the public
   build), the subject lists and the subject pages. A private overlay may put
   one banner above every group. */
import { STRINGS } from '../core/strings.js';
import { parseTime } from '../core/format.js';
import { h } from '../core/h.js';
import { skillItems, sectionItems, wholeGuidance, purposeOf } from '../core/items.js';
import { groupOf, GROUPS, hashFor } from '../core/route.js';
import { DEFAULT_DATA_URL } from '../adapters/web.js';
import { wholeView } from './whole.js';
import { chipSummary, subjectTable } from './cards.js';
import { coverageView } from './coverage.js';
import { alertsView } from './alerts.js';
import { summaryView } from './summary.js';
import { hooksList, hookPage } from './hooks.js';
import { subjectPage } from './subject.js';
import { changesView } from './changes.js';
import { impactView } from './impact.js';
import { opsView } from './ops.js';
import { methodView } from './method.js';
import { searchView } from './search.js';
import { navLink, srcLine, rangeLine, srcLineFor } from './bits.js';
import { fmtUtcDay } from '../core/format.js';
import { indexDoc } from '../core/terms.js';
import { GLOSSES, GLOSS_MISSING } from '../core/glosses.js';

/* How many tested skills had no real-work use in the census window: the ones
   whose count is 0. Nothing without a census. */
function unusedSkills(items, u, refMs) {
  const have = items.filter((i) => i.raw.usage && Number.isInteger(i.raw.usage.invocations));
  if (!u || !have.length) return null;
  const none = have.filter((i) => i.raw.usage.invocations === 0).length;
  return h('p', { class: 'headline-num' }, STRINGS.unusedLine(none, have.length, fmtUtcDay(parseTime(u.from), refMs), fmtUtcDay(parseTime(u.to), refMs)));
}

/* The Skills or the Guidance list: one table row per subject, the coverage and
   that kind's alerts. */
export function buildPage(doc, mode, opts) {
  const o = opts || {};
  const refMs = parseTime(doc.generated_at);
  if (mode === 'guidance') {
    const items = sectionItems(doc);
    return h('div', null,
      rangeLine(doc),
      wholeView(wholeGuidance(doc), refMs),
      h('section', null, h('h2', null, STRINGS.sectionsHeading), h('p', { class: 'note' }, STRINGS.sectionsNote),
        chipSummary(items, mode),
        items.length ? subjectTable(items, 'guidance', refMs) : h('p', null, STRINGS.noCards)),
      coverageView(doc, mode), alertsView(doc, mode));
  }
  const items = skillItems(doc);
  const u = doc.usage;
  return h('div', null,
    rangeLine(doc),
    h('section', null, h('h2', null, STRINGS.skillsHeading), h('p', { class: 'note' }, STRINGS.skillsNote),
      u && typeof u.sessions_scanned === 'number' ? h('p', { class: 'note' }, STRINGS.usageNote(u.sessions_scanned.toLocaleString('en-US'))) : null,
      chipSummary(items, mode),
      unusedSkills(items, u, refMs),
      items.length ? subjectTable(items, 'skills', refMs) : h('p', null, STRINGS.noCards)),
    coverageView(doc, mode), alertsView(doc, mode));
}

function subNav(current) {
  return h('nav', { class: 'subnav', 'aria-label': STRINGS.subNavLabel }, GROUPS.results.map((name) =>
    navLink(hashFor(name), STRINGS.subTabs[name], { id: 'sub-' + name, 'aria-current': name === current ? 'page' : null })));
}

function isSearching(q) {
  return !!(q && (q.text || q.registry || q.verdict || q.model || q.stakes));
}

/* The routes that count days or weeks in UTC and say so once, at the foot. */
export const UTC_ROUTES = ['summary', 'hooks', 'spend'];
/* A skill or guidance page draws the same per-day run chart. */
export const usesUtcDays = (route) => UTC_ROUTES.includes(route.name) || (['skills', 'guidance'].includes(route.name) && !!route.id);

/* opts: { url, ext, search, onFilter, onClear }. `ext` is
   the private build's overlays; the public build passes none. */
export function renderRoute(doc, route, opts) {
  const o = opts || {};
  indexDoc(doc, (d) => purposeOf(d), (id) => (Object.prototype.hasOwnProperty.call(GLOSSES, id) ? GLOSSES[id] : GLOSS_MISSING));
  const ctx = { doc, route, url: o.url || DEFAULT_DATA_URL, ext: o.ext || null, onFilter: o.onFilter, onClear: o.onClear };
  if (isSearching(o.search)) return h('div', null, searchView(doc, o.search, ctx));
  const group = groupOf(route.name);
  let body;
  switch (route.name) {
    case 'needs': body = ctx.ext && ctx.ext.needs ? ctx.ext.needs(ctx) : null; break;
    case 'hooks': body = route.id ? hookPage(doc, route.id, ctx) : hooksList(doc); break;
    case 'skills': body = route.id ? subjectPage(doc, 'skills', route.id, ctx) : buildPage(doc, 'skills', o); break;
    case 'guidance': body = route.id ? subjectPage(doc, 'guidance', route.id, ctx) : buildPage(doc, 'guidance', o); break;
    case 'method': body = methodView(doc, ctx); break;
    case 'changes': body = changesView(doc, ctx); break;
    case 'spend': body = impactView(doc, ctx); break;
    case 'activity': body = opsView(doc, ctx); break;
    default: body = summaryView(doc, ctx);
  }
  const foot = usesUtcDays(route) ? h('p', { class: 'note utc-note' }, STRINGS.utcNote) : null;
  return h('div', null,
    h('h1', { class: 'group-title' }, STRINGS.groups[group]),
    group === 'results' ? subNav(route.name) : null,
    ctx.ext && ctx.ext.banner ? ctx.ext.banner(ctx) : null,
    o.notice ? h('p', { class: 'panel failure' }, o.notice) : null,
    body, foot);
}
