/* View models: one item per card, sorted the way the page shows them. */
import { STRINGS } from './strings.js';
import { parseTime } from './format.js';
import { poolRuns, hasRegression, chipFor, sentenceFor, weeklyGains, gainPerKb, gainOf } from './stats.js';

export function context(doc) {
  const refMs = parseTime(doc.generated_at);
  const roster = (doc.roster && Array.isArray(doc.roster.arms)) ? doc.roster.arms : [];
  return { refMs: refMs, order: roster.map((a) => a && a.model).filter(Boolean), alerts: doc.alerts };
}

/* Skill cards, most helpful first: the loop's keep, then an early sign of
   help, then the test cannot tell, then not enough data, then removal, then
   trending toward removal; by pooled gain
   within each group. */
export const SKILL_RANK = ['helps', 'early', 'canttell', 'insufficient', 'none', 'worse'];
export const SECTION_RANK = ['helps', 'alone', 'early', 'canttell', 'insufficient', 'none', 'worse'];

/* When the loop tests a subject next, as a sort key: queued (by place in
   line), then a re-check (soonest first), then nothing planned, then not on
   the schedule. */
export function nextKey(nt) {
  const n = nt && typeof nt === 'object' ? nt : {};
  if (typeof n.position === 'number' && isFinite(n.position)) return [0, n.position];
  const due = parseTime(n.due);
  if (isFinite(due)) return [1, due];
  return [n.scheduled ? 2 : 3, 0];
}

export function byNext(a, b) {
  const ka = nextKey(a.raw.next_test), kb = nextKey(b.raw.next_test);
  return ka[0] - kb[0] || ka[1] - kb[1];
}

/* How well a subject is faring: its label's rank, then the pooled gain. */
export function byFaring(rank, subject) {
  return (a, b) => {
    const ra = rank.indexOf(a.chip), rb = rank.indexOf(b.chip);
    if (ra !== rb) return ra - rb;
    const ga = gainOf(a.pooled.all, subject), gb = gainOf(b.pooled.all, subject);
    if (ga !== null && gb !== null && ga !== gb) return gb - ga;
    if ((ga === null) !== (gb === null)) return ga === null ? 1 : -1;
    return 0;
  };
}

export const byName = (a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0);

export function skillItems(doc) {
  const c = context(doc);
  const skills = Array.isArray(doc.skills) ? doc.skills : [];
  return skills.filter((s) => s && (s.status === 'covered' || (Array.isArray(s.runs) && s.runs.length)))
    .map((s) => {
      const pooled = poolRuns(s.runs, 'skills', c.refMs, c.order);
      return { name: String(s.name || ''), raw: s, pooled: pooled,
        chip: chipFor(pooled, { subject: 'skills', verdict: s.verdict || null, regression: hasRegression(c.alerts, 'skill', s.name) }),
        sentence: sentenceFor(pooled, 'skills', c.refMs), trend: weeklyGains(s.runs, 'skills', c.refMs) };
    }).sort((a, b) => byNext(a, b) || byFaring(SKILL_RANK)(a, b) || byName(a, b));
}

/* What a skill is for: the first sentence of its SKILL.md description (the
   rest says when it should load, which a reader of this page does not need). */
export function purposeOf(desc) {
  const text = typeof desc === 'string' ? desc.trim() : '';
  if (!text) return null;
  const m = /^[\s\S]*?[.!?](?=\s+[A-Z(]|$)/.exec(text);
  return (m ? m[0] : text).trim();
}

export function sectionItems(doc, sortBy) {
  const c = context(doc);
  const secs = (doc.guidance && Array.isArray(doc.guidance.sections)) ? doc.guidance.sections : [];
  const items = secs.filter((s) => s && s.id).map((s) => {
    const pooled = poolRuns(s.runs, 'guidance', c.refMs, c.order);
    return { id: String(s.id), name: String(s.id), raw: s, pooled: pooled, bytes: Number(s.bytes) || 0,
      chip: chipFor(pooled, { subject: 'guidance', verdict: s.verdict || null, regression: hasRegression(c.alerts, 'guidance', s.id) }),
      sentence: sentenceFor(pooled, 'guidance', c.refMs), trend: weeklyGains(s.runs, 'guidance', c.refMs),
      perKb: gainPerKb(pooled, s.bytes) };
  });
  if (sortBy === 'size') items.sort((a, b) => b.bytes - a.bytes || (a.id < b.id ? -1 : 1));
  else if (sortBy !== 'value') items.sort((a, b) => byNext(a, b) || byFaring(SECTION_RANK, 'guidance')(a, b) || byName(a, b));
  else items.sort((a, b) => {
    if (a.perKb === null && b.perKb === null) return a.id < b.id ? -1 : 1;
    if (a.perKb === null) return 1;
    if (b.perKb === null) return -1;
    return b.perKb - a.perKb || (a.id < b.id ? -1 : 1);
  });
  return items;
}

export function wholeGuidance(doc) {
  const c = context(doc);
  const secs = (doc.guidance && Array.isArray(doc.guidance.sections)) ? doc.guidance.sections : [];
  const runs = [];
  secs.forEach((s) => (Array.isArray(s && s.runs) ? s.runs : []).forEach((r) => runs.push(r)));
  const pooled = poolRuns(runs, 'whole', c.refMs, c.order);
  return { pooled: pooled, chip: chipFor(pooled, { subject: 'whole' }), sentence: sentenceFor(pooled, 'whole', c.refMs),
    trend: weeklyGains(runs, 'whole', c.refMs) };
}
