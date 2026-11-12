/* How the tests work: the loop's stages, the roster, the method, the glossary. */
import { STRINGS } from '../core/strings.js';
import { h } from '../core/h.js';
import { introView } from './intro.js';
import { rosterView } from './roster.js';
import { engineersView } from './engineers.js';
import { panel } from './bits.js';

export function stagesView() {
  return [h('ol', { class: 'stages' }, STRINGS.loopStages.map(([name, text]) => h('li', null, h('strong', null, name), ' ', text))),
    h('p', { class: 'note' }, STRINGS.loopStagesNote)];
}

export function methodView(doc, ctx) {
  const ext = ctx && ctx.ext;
  return h('div', null,
    h('p', { class: 'lead' }, STRINGS.methodLead),
    introView('all'),
    panel(STRINGS.loopHeading, stagesView()),
    rosterView(doc, ext && ext.rosterWhy ? (m) => ext.rosterWhy(ctx, m) : null),
    engineersView(doc, 'skills', ctx && ctx.url),
    engineersView(doc, 'guidance', ctx && ctx.url));
}
