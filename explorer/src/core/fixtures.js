/* Fixture requests, straight from the document's fixture_queue
   (scripts/fixture_queue.py's report): each request followed to its pull
   requests and the fixtures whose `request` names it. */
import { parseTime } from './format.js';
import { DATA_REPO } from '../config.js';

const EVALS_URL = 'https://github.com/' + DATA_REPO;
export const FQ_KINDS = { 'needs-fixtures': 'new fixtures', 'needs-harder-fixtures': 'harder fixtures', 'needs-trigger-set': 'trigger set' };

/* The issue number a fixture's `request` names: the number itself, or the
   last path segment of its issue URL (https://github.com/<repo>/issues/735).
   null when it names none. */
export function requestIssue(request) {
  if (Number.isInteger(request)) return request;
  if (typeof request !== 'string') return null;
  const m = /^(?:\d+|https?:\/\/[^?#\s]*\/(\d+))\/?(?:[?#].*)?$/.exec(request.trim());
  return m ? Number(m[1] || request.trim()) : null;
}

/* null when the document does not report the queue. */
export function fixtureQueue(doc, refMs) {
  const q = doc && doc.fixture_queue;
  if (!q || typeof q !== 'object' || !Array.isArray(q.requests)) return null;
  const fixtures = Array.isArray(q.fixtures) ? q.fixtures.filter((f) => f && typeof f === 'object') : [];
  const rows = q.requests.filter((r) => r && typeof r === 'object' && Number.isInteger(r.issue)).map((req) => {
    const mine = fixtures.filter((f) => requestIssue(f.request) === req.issue);
    const prs = Array.isArray(req.prs) ? req.prs.filter((p) => p && Number.isInteger(p.number)) : [];
    const latest = prs.reduce((a, p) => (!a || p.number > a.number ? p : a), null);
    const opened = parseTime(req.opened_at);
    const open = req.state === 'open';
    return {
      issue: req.issue, issueUrl: EVALS_URL + '/issues/' + req.issue,
      kind: Object.prototype.hasOwnProperty.call(FQ_KINDS, req.kind) ? FQ_KINDS[req.kind] : String(req.kind || 'unknown'),
      subject: String(req.subject || ''), state: open ? 'open' : 'closed', opened,
      ageDays: open && isFinite(opened) && isFinite(refMs) ? (refMs - opened) / 86400000 : null,
      prs: prs.length, prUrl: latest ? EVALS_URL + '/pull/' + latest.number : null,
      merged: prs.some((p) => p.state === 'merged' || p.merged_at),
      fixtures: mine.length, realWork: mine.filter((f) => f.origin_kind === 'real-work').length,
      runs: mine.reduce((s, f) => s + (Number(f.runs) || 0), 0),
      costUsd: mine.reduce((s, f) => s + (Number(f.cost_usd) || 0), 0)
    };
  });
  /* Fixtures whose request is not listed (closed before the queue report
     began), so the rows add up to the totals line. */
  const listed = new Set(rows.map((r) => r.issue));
  const rest = fixtures.filter((f) => !listed.has(requestIssue(f.request)));
  const unlisted = rest.length ? {
    fixtures: rest.length, realWork: rest.filter((f) => f.origin_kind === 'real-work').length,
    runs: rest.reduce((s, f) => s + (Number(f.runs) || 0), 0), costUsd: rest.reduce((s, f) => s + (Number(f.cost_usd) || 0), 0)
  } : null;
  rows.sort((a, b) => (a.state === 'open' ? 0 : 1) - (b.state === 'open' ? 0 : 1) || (a.opened || 0) - (b.opened || 0));
  const findings = Array.isArray(q.findings) ? q.findings.filter((f) => f && typeof f === 'object') : [];
  return { rows, unlisted, totals: q.totals && typeof q.totals === 'object' ? q.totals : {}, findings, fixtures };
}
