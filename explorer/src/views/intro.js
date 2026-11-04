/* What you are looking at, and the glossary. */
import { STRINGS } from '../core/strings.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';

export function introView(mode) {
  const paras = mode === 'guidance' ? STRINGS.introGuidance : STRINGS.introSkills;
  const terms = STRINGS.glossary.concat(mode === 'guidance' ? STRINGS.glossaryGuidance : []);
  const chipKinds = STRINGS.chipOrder.filter((k) => mode === 'guidance' || k !== 'alone');
  return h('section', null,
    h('h2', null, STRINGS.introHeading),
    h('div', { class: 'lead' }, paras.map((p) => h('p', null, p))),
    h('details', { class: 'panel', open: '' },
      h('summary', null, STRINGS.glossaryHeading),
      h('dl', { class: 'gloss' }, terms.map((t) => [h('dt', null, t[0]), h('dd', null, t[1])])),
      h('p', { class: 'note', style: 'margin-top:12px' }, STRINGS.chipGlossaryIntro),
      h('dl', { class: 'gloss' }, chipKinds.map((k) => [h('dt', null, chip(k)), h('dd', null, STRINGS.chipRules[k])]))));
}
