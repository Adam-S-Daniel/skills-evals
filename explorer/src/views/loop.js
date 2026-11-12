/* Loop: the stages, fixture requests, lesson proposals, where lessons went
   and the loop's own pull requests. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtCount } from '../core/format.js';
import { h, link } from '../core/h.js';
import { fixtureQueue } from '../core/fixtures.js';
import { table, srcLine, panel, rangeLine, srcLineFor } from './bits.js';
import { lessonsView } from './lessons.js';
import { barChart, chartTitle } from '../core/charts.js';

const usd = (x) => '$' + (Number(x) || 0).toFixed(2);

export function stagesView() {
  return [h('ol', { class: 'stages' }, STRINGS.loopStages.map(([name, text]) => h('li', null, h('strong', null, name), ' ', text))),
    h('p', { class: 'note' }, STRINGS.loopStagesNote)];
}

export function fixtureRequestsView(doc, refMs) {
  const fq = fixtureQueue(doc, refMs);
  if (!fq) return h('p', { class: 'note' }, STRINGS.fqNone);
  const t = fq.totals;
  const n = (k) => fmtCount(Number(t[k]) || 0);
  const high = fq.findings.filter((f) => f.severity === 'high').length;
  return [srcLineFor(doc, 'queue'), h('p', { class: 'note' }, STRINGS.fqNote),
    h('p', null, STRINGS.fqTotals(n('requests_open'), n('requests_closed'), n('prs_merged'), n('fixtures_real_work'), n('fixtures_invented'), n('fixture_runs'))),
    fq.findings.length ? h('p', { class: 'warn' }, STRINGS.fqFindings(fq.findings.length, high)) : null,
    fq.rows.length ? table([
      { label: STRINGS.colSubject, sort: (r) => r.subject, cell: (r) => link(r.issueUrl, clean(r.subject)) || clean(r.subject) },
      { label: STRINGS.colKind, sort: (r) => r.kind, cell: (r) => r.kind },
      { label: STRINGS.colState, sort: (r) => r.state, cell: (r) => r.state },
      { label: STRINGS.colAge, num: true, sort: (r) => r.ageDays, cell: (r) => (r.ageDays === null ? '' : STRINGS.ageDays(Math.round(r.ageDays))) },
      { label: STRINGS.colPr, sort: (r) => r.prs, cell: (r) => (r.prs ? link(r.prUrl, STRINGS.prState(r.merged, r.prs)) : '') },
      { label: STRINGS.colFixtures, num: true, sort: (r) => r.fixtures, cell: (r) => r.fixtures + ' (' + r.realWork + ')' },
      { label: STRINGS.colRuns, num: true, sort: (r) => r.runs, cell: (r) => fmtCount(r.runs) },
      { label: STRINGS.colCost, num: true, sort: (r) => r.costUsd, cell: (r) => usd(r.costUsd) }
    ], fq.unlisted ? fq.rows.concat([Object.assign({ subject: STRINGS.fqUnlisted, issueUrl: null, kind: '', state: '', ageDays: null, prs: 0 }, fq.unlisted)]) : fq.rows, { tall: true }) : null];
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
export const LOOP_TITLE = /^(New skill: |Improve |Proposed .+ (SKILL\.md|guidance) edit|Retire (skill|guidance section) |Remove .*: no (marginal )?benefit|Trim )/;
export const LOOP_BRANCH = /^(eval-improve|eval-guidance-improve|draft-skill|retire-skill|retire-guidance)\//;

export function isLoopPull(p) {
  if (!p || typeof p !== 'object') return false;
  if (typeof p.head_ref === 'string' && LOOP_BRANCH.test(p.head_ref)) return true;
  return typeof p.title === 'string' && LOOP_TITLE.test(p.title);
}

export function loopPrsView(doc, refMs) {
  const a = doc.activity;
  const rows = (a && Array.isArray(a.pulls) ? a.pulls : []).filter(isLoopPull);
  if (!rows.length) return null;
  return [srcLineFor(doc, 'activity'), h('p', { class: 'note' }, STRINGS.loopPrsNote), prTable(rows, refMs)];
}

export function prTable(rows, refMs) {
  return table([
    { label: STRINGS.colRepo, sort: (p) => p.repo, cell: (p) => clean(String(p.repo).split('/').pop()) },
    { label: STRINGS.colNumber, num: true, sort: (p) => p.number, cell: (p) => link(p.url, '#' + p.number) },
    { label: STRINGS.colTitle, sort: (p) => p.title, cell: (p) => clean(p.title) },
    { label: STRINGS.colState, sort: (p) => p.state, cell: (p) => STRINGS.prStates[p.state] || clean(p.state) },
    { label: STRINGS.colUpdated, sort: (p) => p.merged_at || p.updated_at || p.created_at, cell: (p) => fmtDay(parseTime(p.merged_at || p.updated_at || p.created_at), refMs) }
  ], rows.slice().sort((x, y) => String(y.merged_at || y.updated_at || '').localeCompare(String(x.merged_at || x.updated_at || ''))), { tall: true });
}

export function loopView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const ext = ctx && ctx.ext;
  const stages = ext && ext.loopStages ? ext.loopStages(ctx) : null;
  return h('div', null,
    rangeLine(doc),
    panel(STRINGS.loopHeading, stages || stagesView()),
    ext && ext.loopTop ? ext.loopTop(ctx) : null,
    panel(STRINGS.funnelHeading, funnelView(doc)),
    panel(STRINGS.fqHeading, fixtureRequestsView(doc, refMs)),
    lessonsView(doc, 'all'),
    ext && ext.covers && ext.covers('loop-prs') ? ext.loopPrs(ctx) : panel(STRINGS.loopPrsHeading, loopPrsView(doc, refMs)),
    ext && ext.loopBottom ? ext.loopBottom(ctx) : null);
}
