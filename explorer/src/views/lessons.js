/* Lessons from my sessions (Adam, 2026-11-03). */
import { STRINGS } from '../core/strings.js';
import { clean, githubLink, parseTime, fmtUtcDay } from '../core/format.js';
import { h, link } from '../core/h.js';

export const LESSON_DAY = /^\d{4}-\d{2}-\d{2}$/;
export const lessonDayMs = (d) => (typeof d === 'string' && LESSON_DAY.test(d) ? Date.parse(d + 'T00:00:00Z') : NaN);
export const listWords = (parts) => parts.length < 2 ? parts.join('')
  : parts.slice(0, -1).join(', ') + ' and ' + parts[parts.length - 1];

/* A readable title for a proposal subject, as scripts/mine_sessions.py
   card_title words it; a guidance section by its heading when the page has it. */
export function lessonTitle(subject, headings) {
  const s = String(subject);
  let m = /^tool-([a-z]+)(?:-(.+))?$/.exec(s);
  if (m) {
    const tool = m[1] === 'powershell' ? 'PowerShell' : m[1].charAt(0).toUpperCase() + m[1].slice(1);
    return clean(m[2] ? STRINGS.lessonToolCommand(tool, m[2]) : STRINGS.lessonToolCalls(tool));
  }
  if (s.startsWith('red-ci-') && s.length > 7) return clean(STRINGS.lessonRedCi(s.slice(7)));
  if (s.startsWith('skill:')) return clean(s.slice(6));
  if (s.startsWith('guidance:')) {
    const id = s.slice(9);
    const h = headings && Object.prototype.hasOwnProperty.call(headings, id) ? headings[id] : null;
    return clean(typeof h === 'string' && h ? h : id);
  }
  return clean(s);
}

/* One item, or null when it is off the shape explorer_data.py publishes. */
export function lessonItem(raw) {
  if (!raw || typeof raw !== 'object') return null;
  if (!Object.prototype.hasOwnProperty.call(STRINGS.lessonKinds, raw.kind) || typeof raw.subject !== 'string' || !raw.subject) return null;
  if (!Number.isInteger(raw.evidence_count) || raw.evidence_count < 1) return null;
  if (!isFinite(lessonDayMs(raw.first_seen)) || !isFinite(lessonDayMs(raw.last_seen))) return null;
  let draft = null;
  const d = raw.draft;
  if (d && typeof d === 'object' && Number.isInteger(d.number) && d.number > 0
      && Object.prototype.hasOwnProperty.call(STRINGS.lessonDraftStates, d.state) && githubLink(d.url)) {
    draft = { number: d.number, state: d.state, url: githubLink(d.url) };
  }
  const sources = Array.isArray(raw.sources) ? raw.sources.filter((x) => typeof x === 'string'
    && Object.prototype.hasOwnProperty.call(STRINGS.lessonSurfaces, x)) : null;
  const signals = [];
  if (raw.signals && typeof raw.signals === 'object' && !Array.isArray(raw.signals)) {
    for (const k of Object.keys(STRINGS.lessonSignals)) {
      const n = raw.signals[k];
      if (Number.isInteger(n) && n > 0) signals.push({ signal: k, n: n });
    }
    signals.sort((a, b) => b.n - a.n);
  }
  return { kind: raw.kind, subject: raw.subject, n: raw.evidence_count, first: raw.first_seen, last: raw.last_seen,
    draft: draft, sources: sources, signals: signals };
}

export function lessonSource(it) {
  const where = it.sources && it.sources.length
    ? ' (' + listWords(it.sources.map((x) => STRINGS.lessonSurfaces[x])) + ')' : '';
  const why = it.signals.map((x) => STRINGS.lessonSignalCount(STRINGS.lessonSignals[x.signal], x.n)).join(', ');
  return [h('div', null, STRINGS.lessonTranscripts + where), why ? h('div', { class: 'reason' }, why) : null];
}

export function lessonStatus(it) {
  if (it.kind !== 'new-skill') return STRINGS.lessonWaiting[it.kind];
  if (!it.draft) return STRINGS.lessonNotDrafted;
  return [link(it.draft.url, STRINGS.lessonDraft(it.draft.number)), ' (' + STRINGS.lessonDraftStates[it.draft.state] + ')'];
}

export function lessonLeftOut(lo) {
  const n = (k) => (lo && Number.isInteger(lo[k]) && lo[k] > 0 ? lo[k] : 0);
  const parts = [];
  if (n('memory_note')) parts.push(STRINGS.lessonLeftMemory(n('memory_note')));
  if (n('agent_check')) parts.push(STRINGS.lessonLeftChecks(n('agent_check')));
  if (n('private')) parts.push(STRINGS.lessonLeftPrivate(n('private')));
  return (parts.length ? STRINGS.lessonLeftOut(listWords(parts)) + ' ' : '') + STRINGS.lessonNoText;
}

export const ISSUE_REPO = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/;

/* One memory promotion or skill proposal issue, or null when it is off the
   shape explorer_data.py publishes. */
export function lessonIssue(raw) {
  if (!raw || typeof raw !== 'object') return null;
  if (!Object.prototype.hasOwnProperty.call(STRINGS.lessonIssueSources, raw.source)) return null;
  if (typeof raw.repo !== 'string' || !ISSUE_REPO.test(raw.repo) || !Number.isInteger(raw.number) || raw.number < 1) return null;
  if (!Object.prototype.hasOwnProperty.call(STRINGS.lessonDraftStates, raw.state) || raw.state === 'merged') return null;
  if (!isFinite(lessonDayMs(raw.opened))) return null;
  const url = githubLink(raw.url);
  if (!url) return null;
  const count = Number.isInteger(raw.count) && raw.count >= 0 ? raw.count : null;
  const target = typeof raw.target === 'string' && raw.target ? raw.target : null;
  if (raw.source === 'proposal' && !target) return null;
  return { source: raw.source, repo: raw.repo, number: raw.number, state: raw.state, opened: raw.opened,
    count: count, target: target, url: url };
}

export function lessonIssueTitle(it) {
  if (it.source === 'proposal') return clean(STRINGS.lessonNewSkill(it.target));
  if (it.target === 'agent-checks') return clean(STRINGS.lessonMemoryChecks(it.count, it.repo));
  return clean(STRINGS.lessonMemoryFacts(it.count, it.target, it.repo));
}

/* The skills view lists new-skill and skill:* items and the issue lessons,
   the guidance view guidance:* ones. */
export function lessonsView(doc, mode) {
  const L = doc.lessons;
  const head = h('h2', null, STRINGS.lessonsHeading);
  if (!L || typeof L !== 'object') {
    return h('section', null, head, h('p', { class: 'note' }, STRINGS.lessonsNone));
  }
  const miner = isFinite(lessonDayMs(L.date)) && Array.isArray(L.items);
  const issues = mode === 'guidance' || !Array.isArray(L.issues) ? [] : L.issues.map(lessonIssue).filter(Boolean);
  if (!miner && !issues.length) {
    return h('section', null, head, h('p', { class: 'note' }, STRINGS.lessonsNone));
  }
  const refMs = parseTime(doc.generated_at);
  const headings = {};
  ((doc.guidance && Array.isArray(doc.guidance.sections)) ? doc.guidance.sections : []).forEach((s) => {
    if (s && typeof s.id === 'string' && typeof s.heading === 'string') headings[s.id] = s.heading;
  });
  const items = (miner ? L.items : []).map(lessonItem).filter((it) => it && (mode === 'all' || (mode === 'guidance'
    ? it.subject.startsWith('guidance:')
    : it.kind === 'new-skill' || it.subject.startsWith('skill:'))));
  const day = (d) => fmtUtcDay(lessonDayMs(d), refMs);
  const cols = [STRINGS.colProposal, STRINGS.colKind, STRINGS.colSource, STRINGS.colSeen, STRINGS.colFirst, STRINGS.colLast, STRINGS.colStatus];
  const entry = (closed, n, tr) => ({ closed, n, tr });
  const minerRows = items.map((it) => entry(!!it.draft && it.draft.state !== 'open', it.n, h('tr', null,
    h('td', null, lessonTitle(it.subject, headings)), h('td', null, STRINGS.lessonKinds[it.kind]),
    h('td', null, lessonSource(it)),
    h('td', { class: 'num' }, STRINGS.lessonSeen(it.n)), h('td', { class: 'num' }, day(it.first)),
    h('td', { class: 'num' }, day(it.last)), h('td', null, lessonStatus(it)))));
  const issueRows = issues.map((it) => entry(it.state !== 'open', 0, h('tr', null,
    h('td', null, lessonIssueTitle(it)), h('td', null, STRINGS.lessonIssueKinds[it.source]),
    h('td', null, STRINGS.lessonIssueSources[it.source]),
    h('td', { class: 'num' }, STRINGS.lessonNoValue), h('td', { class: 'num' }, day(it.opened)),
    h('td', { class: 'num' }, STRINGS.lessonNoValue),
    h('td', null, link(it.url, STRINGS.lessonIssueStatus(it.number)), ' (' + STRINGS.lessonDraftStates[it.state] + ')'))));
  // Open proposals first, the most-seen on top; closed ones fold away.
  const rows = minerRows.concat(issueRows).sort((a, b) => a.closed - b.closed || b.n - a.n);
  const grid = (list) => h('div', { class: 'tablewrap' }, h('table', null,
    h('thead', null, h('tr', null, cols.map((c) => h('th', null, c)))), h('tbody', null, list.map((r) => r.tr))));
  const open = rows.filter((r) => !r.closed), shut = rows.filter((r) => r.closed);
  const table = rows.length ? [open.length ? grid(open) : null, shut.length ? h('details', { class: 'history' }, h('summary', null, STRINGS.lessonClosed + ' (' + shut.length + ')'), grid(shut)) : null]
    : h('p', null, mode === 'guidance' ? STRINGS.lessonsEmptyGuidance : STRINGS.lessonsEmptySkills);
  return h('section', null, head,
    h('p', { class: 'lead' }, miner ? STRINGS.lessonsLead(day(L.date)) : STRINGS.lessonMinerNone), table,
    miner ? h('p', { class: 'note', style: 'margin-top:8px' }, lessonLeftOut(L.left_out)) : null);
}
