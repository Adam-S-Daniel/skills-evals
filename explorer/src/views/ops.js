/* Operations: workflow runs, pull requests and issues. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtDateTime } from '../core/format.js';
import { h, link } from '../core/h.js';
import { table, srcLine, panel, rangeLine, srcLineFor } from './bits.js';
import { prTable } from './loop.js';

export const PROBLEM = ['failure', 'timed_out', 'startup_failure', 'cancelled', 'action_required'];

/* A "Problems only" switch that hides the rows marked data-ok, with no re-render. */
export function problemsToggle() {
  return h('label', { class: 'check' }, h('input', { type: 'checkbox', onchange: (e) => {
    const box = e.currentTarget.closest('section');
    if (box) box.classList.toggle('problems-only', e.currentTarget.checked);
  } }), ' ' + STRINGS.problemsOnly);
}

function runsView(doc, refMs) {
  const a = doc.activity;
  if (!a || !Array.isArray(a.runs) || !a.runs.length) return null;
  const rows = a.runs.filter(Boolean).slice().sort((x, y) => (x.created_at < y.created_at ? 1 : -1));
  const state = (r) => r.conclusion || r.state || STRINGS.unknown;
  return [srcLineFor(doc, 'activity'), h('p', { class: 'note' }, STRINGS.opsRunsNote(fmtDateTime(parseTime(a.since)))), problemsToggle(),
    table([
      { label: STRINGS.colWhen, sort: (r) => r.created_at, cell: (r) => fmtDateTime(parseTime(r.created_at)) },
      { label: STRINGS.colState, sort: state, cell: (r) => h('span', { class: 'st ' + (PROBLEM.includes(r.conclusion) ? 'bad' : r.conclusion === 'success' ? 'good' : '') }, clean(state(r))) },
      { label: STRINGS.colRepo, sort: (r) => r.repo, cell: (r) => clean(String(r.repo).split('/').pop()) },
      { label: STRINGS.colWorkflow, sort: (r) => r.workflow, cell: (r) => clean(r.workflow || STRINGS.unknown) },
      { label: STRINGS.colRun, sort: (r) => r.title, cell: (r) => link(r.url, clean(r.title || r.workflow || String(r.run_id))) }
    ], rows, { tall: true, cls: 'console', rowAttrs: (r) => (PROBLEM.includes(r.conclusion) ? null : { 'data-ok': '' }) })];
}

function prsView(doc, refMs) {
  const a = doc.activity;
  if (!a || !Array.isArray(a.pulls) || !a.pulls.length) return null;
  return [srcLineFor(doc, 'activity'), h('p', { class: 'note' }, STRINGS.opsPrsNote), prTable(a.pulls.filter(Boolean), refMs)];
}

function issuesView(doc, refMs) {
  const a = doc.activity;
  if (!a || !Array.isArray(a.issues) || !a.issues.length) return null;
  return [srcLineFor(doc, 'activity'), table([
    { label: STRINGS.colRepo, sort: (i) => i.repo, cell: (i) => clean(String(i.repo).split('/').pop()) },
    { label: STRINGS.colNumber, num: true, sort: (i) => i.number, cell: (i) => link(i.url, '#' + i.number) },
    { label: STRINGS.colTitle, sort: (i) => i.title, cell: (i) => clean(i.title) },
    { label: STRINGS.colUpdated, sort: (i) => i.updated_at, cell: (i) => fmtDay(parseTime(i.updated_at), refMs) }
  ], a.issues.filter(Boolean).slice().sort((x, y) => String(y.updated_at).localeCompare(String(x.updated_at))), { tall: true })];
}

export function opsView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const ext = ctx && ctx.ext;
  const covers = (k) => !!(ext && ext.covers && ext.covers(k));
  return h('div', null,
    rangeLine(doc),
    ext && ext.opsTop ? ext.opsTop(ctx) : null,
    covers('runs') ? ext.runs(ctx) : panel(STRINGS.opsRuns, runsView(doc, refMs)),
    covers('prs') ? ext.prs(ctx) : panel(STRINGS.opsPrs, prsView(doc, refMs)),
    covers('issues') ? ext.issues(ctx) : panel(STRINGS.opsIssues, issuesView(doc, refMs)),
    ext && ext.opsBottom ? ext.opsBottom(ctx) : null);
}
