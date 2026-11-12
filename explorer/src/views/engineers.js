/* For engineers: every run behind the numbers. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, parseTime, fmtDay, fmtCount } from '../core/format.js';
import { normRun } from '../core/stats.js';
import { h, link } from '../core/h.js';
import { table } from './bits.js';

export function engineersView(doc, mode, url) {
  const guidance = mode === 'guidance';
  const subjects = guidance
    ? ((doc.guidance && doc.guidance.sections) || []).filter(Boolean).map((s) => ({ name: s.id, runs: s.runs, verdict: s.verdict, reason: s.verdict_reason, alone: s.alone_verdict }))
    : (doc.skills || []).filter(Boolean).map((s) => ({ name: s.name, runs: s.runs, verdict: s.verdict, reason: s.verdict_reason }));
  const refMs = parseTime(doc.generated_at);
  const cell = (a) => a ? fmtCount(a.passed) + '/' + fmtCount(a.total) : '';
  const RUN_COLS = [STRINGS.colName, STRINGS.colFixture, STRINGS.colModel, STRINGS.colWhen, STRINGS.colCli]
    .concat(guidance ? [STRINGS.colSection, STRINGS.colNone, STRINGS.colFull, STRINGS.colAblated] : [STRINGS.colWith, STRINGS.colWithout])
    .concat([STRINGS.colReport]);
  const rows = [];
  subjects.forEach((s) => (Array.isArray(s.runs) ? s.runs : []).forEach((raw) => {
    const r = normRun(raw, guidance ? 'guidance' : 'skills');
    if (!r) return;
    const l = link(r.url, STRINGS.report);
    const cells = [clean(s.name), clean(r.fixture), friendlyModel(r.model), fmtDay(r.at, refMs), clean(r.cli)]
      .concat(guidance ? [cell(r.with), cell(r.without), cell(r.full), cell(r.ablated)] : [cell(r.with), cell(r.without)]).concat([l]);
    rows.push({ cells });
  }));
  // The date and every score are numbers; the report link is the last cell.
  const runCols = RUN_COLS.map((label, i) => ({ label, num: i >= 3 && i < RUN_COLS.length - 1, cell: (r) => r.cells[i] }));
  const verdicts = subjects.filter((s) => s.verdict || s.reason).map((s) => ({ name: clean(s.name),
    verdict: clean(s.verdict) + (s.alone ? ' / ' + clean(s.alone) : '') + (s.reason ? ': ' + clean(s.reason) : '') }));
  const src = doc.source || {};
  const short = (x) => /^[0-9a-f]{7,40}$/.test(String(x || '')) ? String(x).slice(0, 12) : STRINGS.unknown;
  return h('section', null, h('details', { class: 'panel' }, h('summary', null, STRINGS.engineersHeading),
    h('p', { class: 'note' }, STRINGS.engineersIntro),
    h('p', { class: 'note' }, STRINGS.dataFile(url)),
    src.repository ? h('p', { class: 'note' }, STRINGS.source(clean(src.repository), short(src.repository_commit), short(src.results_commit))) : null,
    table(runCols, rows, { label: STRINGS.engineersHeading }),
    verdicts.length ? table([{ label: STRINGS.colName, cell: (v) => v.name }, { label: STRINGS.colVerdict, cell: (v) => v.verdict }], verdicts, { label: STRINGS.colVerdict }) : null));
}
