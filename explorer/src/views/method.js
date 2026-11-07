/* How the tests work (the roster, the method, the glossary) and what the
   evals removed. */
import { STRINGS } from '../core/strings.js';
import { h } from '../core/h.js';
import { introView } from './intro.js';
import { rosterView } from './roster.js';
import { engineersView } from './engineers.js';
import { removedView, removedSkillsView } from './removed.js';

export function methodView(doc, ctx) {
  const ext = ctx && ctx.ext;
  return h('div', null,
    h('p', { class: 'lead' }, STRINGS.methodLead),
    introView('all'),
    rosterView(doc, ext && ext.rosterWhy ? (m) => ext.rosterWhy(ctx, m) : null),
    engineersView(doc, 'skills', ctx && ctx.url),
    engineersView(doc, 'guidance', ctx && ctx.url));
}

export function removedPage(doc) {
  const a = removedSkillsView(doc), b = removedView(doc);
  return h('div', null, a, b, a || b ? null : h('p', null, STRINGS.removedNone));
}
