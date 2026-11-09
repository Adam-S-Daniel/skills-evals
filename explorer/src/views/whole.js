/* Does the guidance help at all? The whole-guidance headline. */
import { STRINGS } from '../core/strings.js';
import { clean } from '../core/format.js';
import { h } from '../core/h.js';
import { termify, SENTENCE_TERMS } from '../core/terms.js';
import { chip } from '../core/charts.js';
import { trendChart } from './trend.js';
import { modelCharts, legendFor } from './models.js';

/* `whole` is core/items.js wholeGuidance(doc). */
export function wholeView(whole, refMs) {
  return h('section', { class: 'headline' }, h('h2', null, STRINGS.wholeHeading),
    h('div', { class: 'panel' },
      h('div', { class: 'head', style: 'display:flex;gap:8px;justify-content:space-between;align-items:flex-start' },
        h('p', { class: 'answer' }, STRINGS.wholeAnswer[whole.chip]), chip(whole.chip, STRINGS.wholeRule)),
      h('p', { class: 'note' }, STRINGS.wholeNote),
      h('p', { class: 'sent' }, termify(clean(whole.sentence), SENTENCE_TERMS)),
      legendFor('whole', whole.pooled), h('div', { class: 'cols' }, modelCharts(whole.pooled, 'whole')),
      trendChart(whole.trend, refMs, false, 'whole')));
}
