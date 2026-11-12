/* The loop's records the Changes page shows: fixture requests, where lessons
   went, and which pull requests are the loop's own. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtCount, fmtUsd } from '../core/format.js';
import { h, link } from '../core/h.js';
import { fixtureQueue } from '../core/fixtures.js';
import { table, srcLineFor } from './bits.js';
import { barChart, chartTitle } from '../core/charts.js';

const usd = (x) => fmtUsd(Number(x) || 0);

/* What fixture_queue.py's findings say, by kind (read off the finding id), and
   each one as a link to what it names. */
const FINDING_ID = /fixture-queue-(stale-request|stuck-pr|unused-fixture)-/;
const findingKind = (f) => { const m = FINDING_ID.exec(String(f.finding_id || '')); return m ? m[1] : 'other'; };
function findingsView(list) {
  if (!list.length) return null;
  const kinds = Object.keys(STRINGS.fqFindingKinds).filter((k) => list.some((f) => findingKind(f) === k))
    .map((k) => STRINGS.fqFindingKinds[k](list.filter((f) => findingKind(f) === k).length)).join('; ');
  return [h('p', { class: 'warn' }, STRINGS.fqFindings(kinds)),
    h('ul', { class: 'plain' }, list.map((f) => h('li', null, link(f.url, clean(f.subject || f.finding_id)) || clean(f.subject || f.finding_id))))];
}

export function fixtureRequestsView(doc, refMs) {
  const fq = fixtureQueue(doc, refMs);
  if (!fq) return h('p', { class: 'note' }, STRINGS.fqNone);
  const t = fq.totals;
  const n = (k) => fmtCount(Number(t[k]) || 0);
  return [srcLineFor(doc, 'queue'), h('p', { class: 'note' }, STRINGS.fqNote),
    h('p', null, STRINGS.fqTotals(n('requests_open'), n('requests_closed'), n('prs_merged'), n('fixtures_real_work'), n('fixtures_invented'), n('fixture_runs'))),
    findingsView(fq.findings),
    fq.rows.length ? table([
      { label: STRINGS.colSubject, sort: (r) => r.subject, cell: (r) => link(r.issueUrl, clean(r.subject)) || clean(r.subject) },
      { label: STRINGS.colKind, sort: (r) => r.kind, cell: (r) => r.kind },
      { label: STRINGS.colState, sort: (r) => r.state, cell: (r) => r.state },
      { label: STRINGS.colAge, num: true, sort: (r) => r.ageDays, cell: (r) => (r.ageDays === null ? '' : STRINGS.ageDays(Math.round(r.ageDays))) },
      { label: STRINGS.colPr, sort: (r) => r.prs, cell: (r) => (r.prs ? link(r.prUrl, STRINGS.prState(r.merged, r.prs)) : '') },
      { label: STRINGS.colFixtures, num: true, sort: (r) => r.fixtures, cell: (r) => r.fixtures + ' (' + r.realWork + ')' },
      { label: STRINGS.colRuns, num: true, sort: (r) => r.runs, cell: (r) => fmtCount(r.runs) },
      { label: STRINGS.colCost, num: true, sort: (r) => r.costUsd, cell: (r) => usd(r.costUsd) }
    ], fq.rows, { tall: true, foot: [fq.unlisted && Object.assign({ subject: STRINGS.fqUnlisted }, fq.unlisted), fq.noRequest && Object.assign({ subject: STRINGS.fqNoRequest }, fq.noRequest)]
      .filter(Boolean).map((r) => Object.assign({ issueUrl: null, kind: '', state: '', ageDays: null, prs: 0 }, r)) }) : null];
}

const FUNNEL_KEYS = ['check', 'skill', 'guidance', 'nothing', 'open', 'unknown'];
const FUNNEL_COLORS = { check: 'var(--good)', skill: 'var(--s1)', guidance: 'var(--s3)', nothing: 'var(--axis)', open: 'var(--warning)', unknown: 'var(--base)' };

export function funnelView(doc) {
  const f = doc.lesson_funnel;
  if (!f || typeof f !== 'object') return null;
  const c = (k) => (Number.isInteger(f[k]) ? f[k] : 0);
  const decided = c('check') + c('skill') + c('guidance') + c('nothing');
  const all = FUNNEL_KEYS.reduce((s, k) => s + c(k), 0);
  const pct = decided ? Math.round((c('check') / decided) * 100) + '%' : '0%';
  const sources = f.by_source && typeof f.by_source === 'object' ? Object.keys(f.by_source) : [];
  const missing = Array.isArray(f.sources_missing) ? f.sources_missing.filter((s) => STRINGS.funnelSources[s]) : [];
  return [h('p', { class: 'headline-num' }, STRINGS.funnelHeadline(pct, fmtCount(decided))),
    chartTitle(STRINGS.funnelTitle),
    barChart(FUNNEL_KEYS.filter((k) => c(k) > 0).map((k) => ({ label: STRINGS.funnelKinds[k], p: c(k), t: all, color: FUNNEL_COLORS[k] })), STRINGS.funnelHeading),
    sources.length ? table([{ label: STRINGS.colSource, sort: (s) => s, cell: (s) => STRINGS.funnelSources[s] || clean(s) }]
      .concat(FUNNEL_KEYS.map((k) => ({ label: STRINGS.funnelKinds[k], num: true, sort: (s) => f.by_source[s][k], cell: (s) => fmtCount(f.by_source[s][k] || 0) }))), sources) : null,
    missing.length ? h('p', { class: 'note' }, STRINGS.funnelMissing(missing.map((s) => STRINGS.funnelSources[s]).join(', '))) : null];
}

/* The loop's own pull requests in the public repos. By head branch when the
   document carries it (`activity.pulls[].head_ref`; the lasting rule, as the
   private build uses), else by the titles the gates give them
   (scripts/draft_new_skill.py, improve_gate.py, guidance_improve_gate.py,
   retire_skill.py), which older documents need. */
const LOOP_SOURCES = [
  ['editSkill', 'eval-improve', 'Improve |Proposed .+ SKILL\\.md edit|Trim '],
  ['editGuidance', 'eval-guidance-improve', 'Proposed .+ guidance edit'],
  ['newSkill', 'draft-skill', 'New skill: '],
  ['removeSkill', 'retire-skill', 'Retire skill |Remove .*: (?:no (?:marginal )?benefit|unused)'],
  ['removeSection', 'retire-guidance', 'Retire guidance section ']];
/* One row per kind of loop change: its head branch prefix and its title. The
   two patterns below and the changes list's kinds all come from this table. */
export const LOOP_KINDS = LOOP_SOURCES.map(([kind, branch, title]) => ({ kind, branch: new RegExp('^' + branch + '/'), title: new RegExp('^(?:' + title + ')') }));
export const LOOP_TITLE = new RegExp('^(?:' + LOOP_SOURCES.map((k) => k[2]).join('|') + ')');
export const LOOP_BRANCH = new RegExp('^(?:' + LOOP_SOURCES.map((k) => k[1]).join('|') + ')/');

export function isLoopPull(p) {
  if (!p || typeof p !== 'object') return false;
  if (typeof p.head_ref === 'string') return LOOP_BRANCH.test(p.head_ref);
  return typeof p.title === 'string' && LOOP_TITLE.test(p.title);
}

/* Pull request and issue lists show this many rows before "Show all". */
export const LIST_CAP = 6;
/* "skills-evals #961", linked, so the repo and the number share one column. */
export function repoNumber(repo, number, url) {
  const text = clean(String(repo).split('/').pop()) + ' #' + number;
  return link(url, text) || text;
}

export function prTable(rows, refMs) {
  return table([
    { label: STRINGS.colRepoNumber, sort: (p) => p.repo + '#' + String(p.number).padStart(9, '0'), cell: (p) => repoNumber(p.repo, p.number, p.url) },
    { label: STRINGS.colTitle, sort: (p) => p.title, cell: (p) => clean(p.title) },
    { label: STRINGS.colUpdated, sort: (p) => p.merged_at || p.updated_at || p.created_at,
      cell: (p) => (STRINGS.prStates[p.state] || clean(p.state)) + ' ' + fmtDay(parseTime(p.merged_at || p.updated_at || p.created_at), refMs) }
  ], rows.slice().sort((x, y) => String(y.merged_at || y.updated_at || '').localeCompare(String(x.merged_at || x.updated_at || ''))), { tall: true, cap: LIST_CAP });
}
