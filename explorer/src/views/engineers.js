/* For engineers: every run behind the numbers. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, parseTime, fmtDay, fmtCount } from '../core/format.js';
import { normRun } from '../core/stats.js';
import { h, link } from '../core/h.js';

export function engineersView(doc, mode, url) {
  const guidance = mode === 'guidance';
  const subjects = guidance
    ? ((doc.guidance && doc.guidance.sections) || []).filter(Boolean).map((s) => ({ name: s.id, runs: s.runs, verdict: s.verdict, reason: s.verdict_reason, alone: s.alone_verdict }))
    : (doc.skills || []).filter(Boolean).map((s) => ({ name: s.name, runs: s.runs, verdict: s.verdict, reason: s.verdict_reason }));
  const refMs = parseTime(doc.generated_at);
  const cell = (a) => a ? fmtCount(a.passed) + '/' + fmtCount(a.total) : '';
  const head = [STRINGS.colName, STRINGS.colFixture, STRINGS.colModel, STRINGS.colWhen, STRINGS.colCli]
    .concat(guidance ? [STRINGS.colSection, STRINGS.colNone, STRINGS.colFull, STRINGS.colAblated] : [STRINGS.colWith, STRINGS.colWithout])
    .concat([STRINGS.colReport]);
  const rows = [];
  subjects.forEach((s) => (Array.isArray(s.runs) ? s.runs : []).forEach((raw) => {
    const r = normRun(raw, guidance ? 'guidance' : 'skills');
    if (!r) return;
    const l = link(r.url, STRINGS.report);
    rows.push(h('tr', null, h('td', null, clean(s.name)), h('td', null, clean(r.fixture)), h('td', null, friendlyModel(r.model)),
      h('td', { class: 'num' }, fmtDay(r.at, refMs)), h('td', { class: 'num' }, clean(r.cli)),
      guidance ? [h('td', { class: 'num' }, cell(r.with)), h('td', { class: 'num' }, cell(r.without)), h('td', { class: 'num' }, cell(r.full)), h('td', { class: 'num' }, cell(r.ablated))]
        : [h('td', { class: 'num' }, cell(r.with)), h('td', { class: 'num' }, cell(r.without))],
      h('td', null, l)));
  }));
  const verdicts = subjects.filter((s) => s.verdict || s.reason).map((s) => h('tr', null, h('td', null, clean(s.name)),
    h('td', null, clean(s.verdict) + (s.alone ? ' / ' + clean(s.alone) : '') + (s.reason ? ': ' + clean(s.reason) : ''))));
  const src = doc.source || {};
  const short = (x) => /^[0-9a-f]{7,40}$/.test(String(x || '')) ? String(x).slice(0, 12) : STRINGS.unknown;
  return h('section', null, h('details', { class: 'panel' }, h('summary', null, STRINGS.engineersHeading),
    h('p', { class: 'note' }, STRINGS.engineersIntro),
    h('p', { class: 'note' }, STRINGS.dataFile(url)),
    src.repository ? h('p', { class: 'note' }, STRINGS.source(clean(src.repository), short(src.repository_commit), short(src.results_commit))) : null,
    h('div', { class: 'tablewrap' }, h('table', null, h('thead', null, h('tr', null, head.map((c) => h('th', null, c)))), h('tbody', null, rows))),
    verdicts.length ? h('div', { class: 'tablewrap', style: 'margin-top:12px' }, h('table', null,
      h('thead', null, h('tr', null, h('th', null, STRINGS.colName), h('th', null, STRINGS.colVerdict))), h('tbody', null, verdicts))) : null));
}
