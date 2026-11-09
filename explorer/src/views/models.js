/* Per-model bar charts and their legend. */
import { STRINGS } from '../core/strings.js';
import { friendlyModel } from '../core/format.js';
import { h } from '../core/h.js';
import { defn } from '../core/terms.js';
import { barChart, legend, chartTitle } from '../core/charts.js';

export function modelCharts(pooled, subject) {
  return pooled.models.filter((m) => m.n > 0 || m.nAbl > 0).map((m) => {
    const name = friendlyModel(m.model);
    let rows;
    if (subject === 'guidance') {
      rows = [];
      if (m.n > 0) {
        rows.push({ label: STRINGS.barSection, p: m.wp, t: m.wt, color: 'var(--s1)' });
        rows.push({ label: STRINGS.barNone, p: m.op, t: m.ot, color: 'var(--s2)' });
      }
      if (m.nAbl > 0) {
        rows.push({ label: STRINGS.barAll, p: m.fp, t: m.ft, color: 'var(--axis)' });
        rows.push({ label: STRINGS.barAblated, p: m.ap, t: m.at, color: 'var(--s3)' });
      }
    } else if (subject === 'whole') {
      rows = [{ label: STRINGS.barWholeFull, p: m.wp, t: m.wt, color: 'var(--s1)' },
        { label: STRINGS.barWholeNone, p: m.op, t: m.ot, color: 'var(--s2)' }];
    } else {
      rows = [{ label: STRINGS.barWith, p: m.wp, t: m.wt, color: 'var(--s1)' },
        { label: STRINGS.barWithout, p: m.op, t: m.ot, color: 'var(--s2)' }];
    }
    return h('div', null,
      chartTitle(STRINGS.barTitle[subject === 'guidance' ? 'guidance' : subject === 'whole' ? 'whole' : 'skills'](name)),
      h('p', { class: 'model' }, Math.max(m.n, m.nAbl) + ' ', defn('comparisonRun', Math.max(m.n, m.nAbl) === 1 ? 'comparison run' : 'comparison runs'),
        m.judgeWith !== null && m.judgeWithout !== null ? ['; ', defn('judge', 'judge score'), ' ' + m.judgeWith.toFixed(1) + ' with, ' + m.judgeWithout.toFixed(1) + ' without (out of 10)'] : null),
      barChart(rows, STRINGS.chartLabel(name)));
  });
}

/* Whether a section's pooled runs carry its section-alone pair (only this
   section vs no guidance), which the data file publishes only when it
   factors into the section's decision. */
export function hasAlone(pooled) { return pooled.models.some((m) => m.n > 0); }

export function legendFor(subject, pooled) {
  if (subject === 'guidance') {
    const D = STRINGS.barDefs;
    const items = hasAlone(pooled) ? [{ label: STRINGS.barSection, color: 'var(--s1)', def: D.section }, { label: STRINGS.barNone, color: 'var(--s2)', def: D.none }] : [];
    if (pooled.models.some((m) => m.nAbl > 0)) {
      items.push({ label: STRINGS.barAll, color: 'var(--axis)', def: D.all });
      items.push({ label: STRINGS.barAblated, color: 'var(--s3)', def: D.ablated });
    }
    return legend(items);
  }
  if (subject === 'whole') return legend([{ label: STRINGS.barWholeFull, color: 'var(--s1)', def: STRINGS.barDefs.all }, { label: STRINGS.barWholeNone, color: 'var(--s2)', def: STRINGS.barDefs.none }]);
  return legend([{ label: STRINGS.barWith, color: 'var(--s1)', def: STRINGS.barDefs.with }, { label: STRINGS.barWithout, color: 'var(--s2)', def: STRINGS.barDefs.without }]);
}

export function hasData(pooled) { return pooled.models.some((m) => m.n > 0 || m.nAbl > 0); }
