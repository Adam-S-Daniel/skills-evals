/* Coverage: tested, left out on purpose, not yet tested. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtCount } from '../core/format.js';
import { h } from '../core/h.js';

export function coverageView(doc, mode) {
  const list = mode === 'guidance'
    ? ((doc.guidance && Array.isArray(doc.guidance.sections)) ? doc.guidance.sections : []).filter(Boolean).map((s) => ({ name: s.heading || s.id, status: s.status, reason: s.skip_reason }))
    : (Array.isArray(doc.skills) ? doc.skills : []).filter(Boolean).map((s) => ({ name: s.name, status: s.status, reason: s.skip_reason }));
  const group = (status, title) => {
    const rows = list.filter((x) => x.status === status).sort((a, b) => String(a.name) < String(b.name) ? -1 : 1);
    return h('div', { class: 'panel' }, h('h3', null, title + ' (' + rows.length + ')'),
      rows.length ? h('ul', { class: 'plain' }, rows.map((x) => h('li', null, clean(x.name),
        status === 'skipped' && x.reason ? h('div', { class: 'reason' }, clean(x.reason)) : null))) : h('p', { class: 'note' }, STRINGS.noneListed));
  };
  const cov = doc.coverage;
  const census = mode !== 'guidance' && cov && typeof cov.total === 'number'
    ? h('p', { class: 'note' }, STRINGS.census(fmtDay(parseTime(cov.as_of)), fmtCount(cov.total), fmtCount(cov.covered), fmtCount(cov.skipped), fmtCount(cov.gap)))
    : null;
  return h('section', null, h('h2', null, STRINGS.coverageHeading),
    h('p', { class: 'lead' }, mode === 'guidance' ? STRINGS.coverageIntroGuidance : STRINGS.coverageIntroSkills), census,
    h('div', { class: 'cols' }, group('covered', STRINGS.covered), group('skipped', STRINGS.skipped), group('gap', STRINGS.gap)));
}
