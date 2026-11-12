/* A page per subject (a skill or a guidance section): everything measured
   about it in one place. */
import { STRINGS } from '../core/strings.js';
import { GLOSSES, GLOSS_MISSING } from '../core/glosses.js';
import { clean, friendlyModel, parseTime, fmtDay, fmtDateTime, fmtCount, wordsFor, fmtUsd } from '../core/format.js';
import { h, link } from '../core/h.js';
import { chip } from '../core/charts.js';
import { skillItems, sectionItems, purposeOf } from '../core/items.js';
import { fixtureQueue } from '../core/fixtures.js';
import { fixtureTerm, defn, termify, SENTENCE_TERMS } from '../core/terms.js';
import { hashFor } from '../core/route.js';
import { table, rangeLine, navLink, panel, badge, fold } from './bits.js';
import { verdictLine, nextLine, stakesLine, usageLine, copiesLine, discardedLine } from './cards.js';
import { modelCharts, legendFor, hasData, hasAlone } from './models.js';
import { trendChart } from './trend.js';
import { confidenceView } from './range.js';
import { utilityView, decisionsView, utilityTotals } from './utility.js';
import { lessonItem, lessonIssue, lessonTitle, lessonStatus, lessonIssueTitle } from './lessons.js';

const share = (x) => (typeof x === 'number' && isFinite(x) ? Math.round(x * 100) + '%' : STRINGS.noValue);
const usd = (x) => (typeof x === 'number' && isFinite(x) ? fmtUsd(x) : STRINGS.noValue);
const one = (x) => (typeof x === 'number' && isFinite(x) ? fmtCount(x) : STRINGS.noValue);

/* Scored runs of one subject from the document's evals, newest first. A
   guidance section's runs carry skill "guidance/<id>". */
export function runsOf(doc, kind, name) {
  const key = kind === 'guidance' ? 'guidance/' + name : name;
  const e = doc.evals && typeof doc.evals === 'object' ? doc.evals : {};
  const pick = (list) => (Array.isArray(list) ? list : []).filter((r) => r && r.skill === key)
    .sort((a, b) => (a.fired_at < b.fired_at ? 1 : -1));
  return { runs: pick(e.runs), bare: pick(e.bare_runs) };
}

/* The Judge cell. The judge is decided per pair of arms: when the arm with
   the subject passes strictly more checks, it is skipped for both arms;
   a tie or a loss gets both arms judged. Guidance rows are always
   the in-context pair (full vs full minus the section), so they name the
   full-guidance version. with_skill and without_skill are the
   mean checks passed per trial and checks is the total per arm. The row's
   judge field says whether a skip happened: "not run" claims no reason. */
export function judgeCell(r) {
  const num = (x) => typeof x === 'number' && isFinite(x);
  if (num(r.with_judge) && num(r.without_judge)) return STRINGS.judgeRan(r.with_judge.toFixed(1), r.without_judge.toFixed(1));
  const wins = num(r.with_skill) && num(r.without_skill) && r.with_skill > r.without_skill;
  const counted = wins && num(r.checks) && r.checks > 0;
  const skipped = counted ? () => STRINGS.judgeSkipped(
    typeof r.skill === 'string' && r.skill.startsWith('guidance/') ? STRINGS.judgeWithSection : STRINGS.judgeWithSkill,
    fmtCount(r.with_skill), fmtCount(r.without_skill), fmtCount(r.checks)) : () => STRINGS.judgeSkippedBare;
  // The row's own judge field decides whether a skip reason may be claimed.
  if (r.judge === 'not run') return STRINGS.judgeNotRun;
  if (typeof r.judge === 'string' && r.judge.startsWith('skipped')) return skipped();
  // Older documents carry no judge field: fall back to the counts.
  return wins ? skipped() : STRINGS.judgeNotRecorded;
}

export function runsTable(runs, refMs) {
  if (!runs.length) return h('p', { class: 'note' }, STRINGS.runsNone);
  const points = runs.some((r) => typeof r.meter_points === 'number');
  const cols = [
    // The start time links to the report, so the table needs no column for it.
    { label: STRINGS.colStarted, sort: (r) => r.fired_at, cell: (r) => link(r.report_url, fmtDateTime(parseTime(r.fired_at))) || fmtDateTime(parseTime(r.fired_at)) },
    { label: STRINGS.colFixture, sort: (r) => r.fixture, cell: (r) => fixtureTerm(clean(r.fixture)) },
    { label: STRINGS.colModel, sort: (r) => r.model, cell: (r) => friendlyModel(r.model) },
    { label: STRINGS.colWith, num: true, sort: (r) => r.with_share, cell: (r) => one(r.with_skill) + ' (' + share(r.with_share) + ')' },
    { label: STRINGS.colWithout, num: true, sort: (r) => r.without_share, cell: (r) => one(r.without_skill) + ' (' + share(r.without_share) + ')' },
    { label: STRINGS.colJudge, sort: (r) => r.judge, cell: judgeCell },
    { label: STRINGS.colCost, num: true, sort: (r) => r.cost_usd, cell: (r) => usd(r.cost_usd) }
  ];
  if (points) cols.push({ label: STRINGS.colPoints, num: true, sort: (r) => r.meter_points, cell: (r) => one(r.meter_points) });
  return table(cols, runs, { tall: true });
}

export function bareTable(bare) {
  if (!bare.length) return null;
  return [h('p', { class: 'note' }, STRINGS.bareNote), table([
    { label: STRINGS.colStarted, sort: (r) => r.fired_at, cell: (r) => fmtDay(parseTime(r.fired_at)) },
    { label: STRINGS.colFixture, sort: (r) => r.fixture, cell: (r) => fixtureTerm(clean(r.fixture)) },
    { label: STRINGS.colModel, sort: (r) => r.model, cell: (r) => friendlyModel(r.model) },
    { label: STRINGS.colBare, num: true, sort: (r) => r.bare_share, cell: (r) => share(r.bare_share) },
    { label: STRINGS.colWithout, num: true, sort: (r) => r.without_share, cell: (r) => share(r.without_share) },
    { label: STRINGS.colWith, num: true, sort: (r) => r.with_share, cell: (r) => share(r.with_share) },
    { label: STRINGS.colPaired, sort: (r) => r.paired_at, cell: (r) => (r.paired_at ? fmtDay(parseTime(r.paired_at)) : STRINGS.noValue) },
    { label: STRINGS.colReport, cell: (r) => link(r.report_url, STRINGS.report) }
  ], bare)];
}

function copiesTable(c) {
  if (!c || !Array.isArray(c.loaded) || !c.loaded.length) return null;
  return table([
    { label: STRINGS.colCopy, sort: (e) => e.digest, cell: (e) => clean(String(e.digest).slice(0, 12)) },
    { label: STRINGS.colSurface, sort: (e) => e.surface, cell: (e) => clean(e.surface || STRINGS.unknown) },
    { label: STRINGS.colVsMain, sort: (e) => e.vs_main, cell: (e) => STRINGS.vsMain[e.vs_main] || STRINGS.unknown },
    { label: STRINGS.colUses, num: true, sort: (e) => e.invocations, cell: (e) => fmtCount(e.invocations) }
  ], c.loaded.filter((e) => e && typeof e.digest === 'string'));
}

function fixturesPanel(doc, runs, name, refMs) {
  const fq = fixtureQueue(doc, refMs);
  const listed = fq ? fq.fixtures.filter((f) => f.subject === name && typeof f.path === 'string') : [];
  const seen = new Set(listed.map((f) => String(f.path).split('/').pop()));
  const fromRuns = [];
  for (const r of runs) {
    const leaf = String(r.fixture || '').split('/').pop();
    if (leaf && !seen.has(leaf)) { seen.add(leaf); fromRuns.push({ path: r.fixture, origin_kind: null, runs: null }); }
  }
  const rows = listed.concat(fromRuns);
  if (!rows.length) return h('p', { class: 'note' }, STRINGS.fixturesNone);
  return table([
    { label: STRINGS.colFixturePath, sort: (f) => f.path, cell: (f) => fixtureTerm(clean(f.path)) },
    { label: STRINGS.colOrigin, sort: (f) => f.origin_kind || '', cell: (f) => clean(f.origin_kind || STRINGS.unknown) },
    { label: STRINGS.colRuns, num: true, sort: (f) => f.runs, cell: (f) => (f.runs === null || f.runs === undefined ? STRINGS.noValue : fmtCount(f.runs)) }
  ], rows);
}

function lessonsAbout(doc, kind, name, refMs) {
  const L = doc.lessons && typeof doc.lessons === 'object' ? doc.lessons : {};
  const items = (Array.isArray(L.items) ? L.items : []).map(lessonItem).filter((it) => it && (kind === 'guidance'
    ? it.subject === 'guidance:' + name : it.subject === 'skill:' + name || (it.kind === 'new-skill' && it.subject === name)));
  const issues = kind === 'guidance' ? [] : (Array.isArray(L.issues) ? L.issues : []).map(lessonIssue).filter((it) => it && it.target === name);
  if (!items.length && !issues.length) return h('p', { class: 'note' }, STRINGS.lessonsAboutNone);
  return h('ul', { class: 'plain' },
    items.map((it) => h('li', null, lessonTitle(it.subject), ' — ', STRINGS.lessonKinds[it.kind], ', ', STRINGS.lessonSeen(it.n), ' (', lessonStatus(it), ')')),
    issues.map((it) => h('li', null, lessonIssueTitle(it), ' — ', link(it.url, STRINGS.lessonIssueStatus(it.number)), ' (' + STRINGS.lessonDraftStates[it.state] + ')')));
}

/* What the subject's tests cost over the last 30 days, at list price, from its
   run usefulness rows; nothing when it has none. */
function testCost(rows, refMs) {
  const t = Array.isArray(rows) && rows.length ? utilityTotals(rows, '30', refMs).total : null;
  return t && t.runs ? h('p', { class: 'meta' }, STRINGS.testCost(usd(t.cost))) : null;
}

export function subjectPage(doc, kind, name, ctx) {
  const refMs = parseTime(doc.generated_at);
  const guidance = kind === 'guidance';
  const items = guidance ? sectionItems(doc) : skillItems(doc);
  const it = items.find((x) => (guidance ? x.id : x.name) === name);
  const back = h('p', { class: 'back' }, navLink(hashFor(kind), STRINGS.back(STRINGS.subjectBack[kind])));
  if (!it) {
    // A skill the document lists but the loop does not test yet: what it is
    // for, and that it has no results.
    const known = guidance ? null : (Array.isArray(doc.skills) ? doc.skills : []).find((s) => s && s.name === name);
    if (!known) return h('div', null, back, h('p', null, STRINGS.subjectNotFound));
    return h('div', null, back, h('section', { class: 'block subject' },
      h('div', { class: 'subject-head' }, h('h2', { class: 'title' }, clean(name)),
        known.private === true ? badge(STRINGS.privateBadge, 'private') : null),
      rangeLine(doc),
      h('p', { class: 'gl' }, clean(purposeOf(known.description) || STRINGS.purposeMissing)),
      known.registry ? h('p', { class: 'meta' }, STRINGS.registryLine(clean(known.registry))) : null,
      h('p', null, STRINGS.subjectUntested)));
  }
  const raw = it.raw;
  const subj = guidance ? 'guidance' : 'skills';
  const { runs, bare } = runsOf(doc, kind, name);
  const gloss = guidance ? (Object.prototype.hasOwnProperty.call(GLOSSES, it.id) ? GLOSSES[it.id] : GLOSS_MISSING)
    : clean(purposeOf(raw.description) || STRINGS.purposeMissing);
  const ext = ctx && ctx.ext;
  return h('div', null, back,
    h('section', { class: 'block subject' },
      h('div', { class: 'subject-head' }, h('h2', { class: 'title' }, clean(guidance ? raw.heading || it.id : it.name)), chip(it.chip),
        raw.private === true ? badge(STRINGS.privateBadge, 'private') : null),
      rangeLine(doc),
      h('p', { class: 'gl' }, gloss),
      !guidance && raw.registry ? h('p', { class: 'meta' }, STRINGS.registryLine(clean(raw.registry))) : null,
      guidance ? h('p', { class: 'meta' }, STRINGS.size(wordsFor(it.bytes))) : null,
      nextLine(raw.next_test, refMs, guidance ? 'section' : 'skill'),
      guidance ? null : usageLine(raw.usage, doc.usage, refMs),
      testCost(raw.run_utility, refMs),
      stakesLine(raw.stakes),
      h('h3', null, defn('verdict', STRINGS.verdictHeading)),
      verdictLine(raw.verdict) || h('p', { class: 'meta' }, STRINGS.verdict.insufficient),
      raw.verdict_reason ? h('p', { class: 'meta' }, clean(raw.verdict_reason)) : null,
      discardedLine(raw.discarded_runs),
      h('p', { class: 'sent' }, termify(clean(it.sentence), SENTENCE_TERMS)),
      guidance && hasAlone(it.pooled) ? h('p', { class: 'meta' }, STRINGS.aloneShown) : null),
    fold(STRINGS.gainHeading, [confidenceView(raw.confidence, doc.policy, subj),
      hasData(it.pooled) ? h('div', { class: 'cols' }, h('div', null, legendFor(subj, it.pooled), modelCharts(it.pooled, subj)), h('div', null, trendChart(it.trend, refMs, subj))) : null]),
    Array.isArray(raw.run_utility) && raw.run_utility.length
      ? fold(STRINGS.utilityHeading, [utilityView([{ label: STRINGS.utilityThis, rows: raw.run_utility }], refMs),
        decisionsView(raw.decisions, friendlyModel)]) : null,
    fold(STRINGS.runsHeading, runsTable(runs, refMs)),
    fold(STRINGS.bareHeading, bareTable(bare)),
    guidance ? null : panel(STRINGS.useHeading, ext && ext.subjectUse ? ext.subjectUse(ctx, name) : null),
    guidance ? null : fold(STRINGS.copiesHeading, [copiesLine(raw.copies), copiesTable(raw.copies)]),
    fold(STRINGS.fixturesHeading, fixturesPanel(doc, runs, name, refMs)),
    panel(STRINGS.lessonsAbout, lessonsAbout(doc, kind, name, refMs)));
}
