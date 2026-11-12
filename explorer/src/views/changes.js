/* Changes: what the loop changed, newest first, with the reason, then the
   rest of the loop's own record (trending toward removal, where lessons went,
   fixture requests, lesson proposals). The list is built from facts the
   document already holds: the loop's merged pull requests, the removed-skill
   and removed-section lists, and the checks and sections agents made. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtCount } from '../core/format.js';
import { h, link } from '../core/h.js';
import { hashFor } from '../core/route.js';
import { table, panel, navLink, rangeLine, srcLineFor } from './bits.js';
import { isLoopPull, funnelView, fixtureRequestsView } from './loop.js';
import { lessonsView } from './lessons.js';
import { trendingView } from './trending.js';

export const CHANGE_DAYS = 30;
const DAY_MS = 86400000;
const KIND_ROUTE = { newSkill: 'skills', editSkill: 'skills', removeSkill: 'skills', removeSection: 'guidance', editGuidance: 'guidance', newSection: 'guidance', newCheck: 'hooks' };
const KINDS = [['editSkill', /^eval-improve\//, /^(Improve |Proposed .+ SKILL\.md edit|Trim )/], ['editGuidance', /^eval-guidance-improve\//, /^Proposed .+ guidance edit/],
  ['newSkill', /^draft-skill\//, /^New skill: /], ['removeSkill', /^retire-skill\//, /^(Retire skill |Remove )/], ['removeSection', /^retire-guidance\//, /^Retire guidance section /]];
export const REMOVALS = ['removeSkill', 'removeSection'];

/* What kind of change a loop pull request is, by head branch when the
   document carries it (the lasting rule), else by the title the gate gives it. */
export function pullKind(p) {
  const ref = typeof p.head_ref === 'string' ? p.head_ref : '', title = String(p.title || '');
  for (const [kind, branch, name] of KINDS) if (branch.test(ref) || name.test(title)) return kind;
  return null;
}

/* The skill or section a loop pull request is about, read from its title. */
export function pullSubject(p) {
  const t = String(p.title || '').replace(/`/g, '');
  const m = /^New skill: (\S+)/.exec(t) || /^Proposed (\S+) (?:SKILL\.md|guidance) edit/.exec(t) || /^Improve (\S+)/.exec(t) || /^Trim (\S+)/.exec(t)
    || /^Remove (?:[\w.-]+\/)?([\w.-]+): /.exec(t) || /^Retire (?:skill|guidance section) ([\w.-]+?):?(?: |$)/.exec(t);
  return m ? m[1] : null;
}

/* One sentence for why a removal happened, from the reason its pull request
   title gives; the generic one when there is no title to read. */
function removalWhy(kind, title) {
  const W = STRINGS.changeWhy;
  if (kind === 'removeSection') return W.removeSection;
  if (/: unused/.test(title || '')) return W.removeUnused;
  if (/no (marginal )?benefit/.test(title || '')) return W.removeNoBenefit;
  return W.removeSkill;
}

const num = (v) => (Number.isInteger(v) ? v : 0);
function checkWhy(m) {
  const runs = num(m && m.runs), blocked = num(m && m.blocked);
  return runs ? STRINGS.changeWhy.checkRan(fmtCount(runs), fmtCount(blocked)) : STRINGS.changeWhy.checkNew;
}

/* The rows of the list, newest first: { kind, when, subject, why, pr, undo }.
   `extra` is more pull requests in the document's own shape, which the private
   build adds from its live reads; one already listed (same address) is skipped.
   The window is the last CHANGE_DAYS before the document; every removal is
   kept, so the removals-only view is the whole history. */
export function changeRows(doc, extra) {
  const refMs = parseTime(doc.generated_at);
  const since = isFinite(refMs) ? refMs - CHANGE_DAYS * DAY_MS : -Infinity;
  const a = doc.activity;
  const seen = new Set();
  const pulls = (a && Array.isArray(a.pulls) ? a.pulls : []).concat(Array.isArray(extra) ? extra : [])
    .filter((p) => p && typeof p === 'object' && isLoopPull(p) && p.state === 'merged' && !seen.has(p.url) && seen.add(p.url));
  const lessons = (doc.lessons && Array.isArray(doc.lessons.items) ? doc.lessons.items : []).filter((l) => l && l.kind === 'new-skill');
  const rows = [];
  const claimed = new Set();
  const removed = [['removeSkill', doc.removed_skills, 'name'], ['removeSection', doc.guidance && doc.guidance.removed, 'id']]
    .flatMap(([kind, list, key]) => (Array.isArray(list) ? list : []).filter((r) => r && typeof r[key] === 'string' && typeof r.date === 'string')
      .map((r) => ({ kind, subject: r[key], date: r.date, undo: r.reverse_url })));
  for (const r of removed) {
    const pr = pulls.find((p) => pullKind(p) === r.kind && pullSubject(p) === r.subject);
    if (pr) claimed.add(pr.url);
    rows.push({ kind: r.kind, when: parseTime(r.date + 'T12:00:00Z'), subject: r.subject, why: removalWhy(r.kind, pr && pr.title), pr: pr || null, undo: r.undo });
  }
  for (const p of pulls) {
    const kind = pullKind(p);
    const when = parseTime(p.merged_at);
    if (!kind || claimed.has(p.url) || !(when >= since)) continue;
    const subject = pullSubject(p);
    let why;
    if (kind === 'newSkill') {
      const l = lessons.find((x) => x.subject === subject);
      why = l && Number.isInteger(l.evidence_count) ? STRINGS.changeWhy.newSkillLessons(fmtCount(l.evidence_count)) : STRINGS.changeWhy.newSkill;
    } else if (REMOVALS.includes(kind)) why = removalWhy(kind, p.title);
    else why = STRINGS.changeWhy[kind];
    rows.push({ kind, when, subject, why, pr: p, undo: null });
  }
  // Checks and sections an agent or the loop made have no pull request in the
  // document; a skill is listed here only when no new-skill pull request is.
  const made = doc.agent_made && Array.isArray(doc.agent_made.items) ? doc.agent_made.items : [];
  const listedSkills = new Set(rows.filter((r) => r.kind === 'newSkill').map((r) => r.subject));
  for (const i of made) {
    if (!i || (i.origin !== 'agent' && i.origin !== 'loop') || typeof i.id !== 'string') continue;
    const when = parseTime(i.created);
    if (!(when >= since)) continue;
    if (i.kind === 'check') rows.push({ kind: 'newCheck', when, subject: i.id, why: checkWhy(i.impact), pr: null, undo: null });
    else if (i.kind === 'section') rows.push({ kind: 'newSection', when, subject: i.id, why: STRINGS.changeWhy.newSection, pr: null, undo: null });
    else if (i.kind === 'skill' && !listedSkills.has(i.id)) rows.push({ kind: 'newSkill', when, subject: i.id, why: STRINGS.changeWhy.newSkill, pr: null, undo: null });
  }
  return rows.sort((x, y) => (y.when - x.when) || (x.subject < y.subject ? -1 : x.subject > y.subject ? 1 : 0));
}

export function changesList(doc, filter, extra) {
  const all = changeRows(doc, extra);
  const refMs = parseTime(doc.generated_at);
  const rows = filter === 'removed' ? all.filter((r) => REMOVALS.includes(r.kind)) : all.filter((r) => !isFinite(refMs) || r.when >= refMs - CHANGE_DAYS * DAY_MS);
  const nav = h('p', { class: 'filters' }, filter === 'removed' ? navLink(hashFor('changes'), STRINGS.changesAll) : h('strong', null, STRINGS.changesAll), ' · ',
    filter === 'removed' ? h('strong', null, STRINGS.changesRemovedOnly) : navLink(hashFor('changes', 'removed'), STRINGS.changesRemovedOnly));
  return [srcLineFor(doc, 'activity'), h('p', { class: 'note' }, filter === 'removed' ? STRINGS.changesRemovedNote : STRINGS.changesNote(CHANGE_DAYS)), nav,
    rows.length ? table([
      { label: STRINGS.colWhen, sort: (r) => r.when, cell: (r) => fmtDay(r.when, refMs) },
      { label: STRINGS.colChange, sort: (r) => r.kind, cell: (r) => STRINGS.changeKinds[r.kind] },
      { label: STRINGS.colSubject, sort: (r) => r.subject, cell: (r) => (r.subject ? navLink(hashFor(KIND_ROUTE[r.kind], r.subject), clean(r.subject)) : STRINGS.noValue) },
      { label: STRINGS.colWhy, cell: (r) => r.why },
      { label: STRINGS.colPr, sort: (r) => (r.pr ? r.pr.number : 0), cell: (r) => (r.pr ? link(r.pr.url, clean(String(r.pr.repo).split('/').pop()) + ' #' + r.pr.number) : '') },
      { label: STRINGS.colUndo, cell: (r) => (r.undo ? link(r.undo, STRINGS.changeUndo) : '') }
    ], rows, { tall: true }) : h('p', null, filter === 'removed' ? STRINGS.removedNone : STRINGS.changesNone(CHANGE_DAYS))];
}

export function changesView(doc, ctx) {
  const ext = ctx && ctx.ext;
  const extra = ext && ext.changePulls ? ext.changePulls() : [];
  const filter = ctx && ctx.route && ctx.route.id === 'removed' ? 'removed' : null;
  return h('div', null,
    rangeLine(doc),
    panel(STRINGS.changesHeading, changesList(doc, filter, extra)),
    filter ? null : [trendingView(doc, 'all'), panel(STRINGS.funnelHeading, funnelView(doc)), panel(STRINGS.fqHeading, fixtureRequestsView(doc, parseTime(doc.generated_at))), lessonsView(doc, 'all')]);
}
