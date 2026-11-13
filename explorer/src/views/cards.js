/* The lines a subject's page and the Skills and Guidance tables share, and the counts line above the table. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtUtcDay, wordsFor, fmtUsd, fmtCount } from '../core/format.js';
import { h, link } from '../core/h.js';
import { chip } from '../core/charts.js';
import { purposeOf, nextKey } from '../core/items.js';
import { gainOf, gainPer100Words, runsOf } from '../core/stats.js';
import { hashFor } from '../core/route.js';
import { navLink, table, badge } from './bits.js';
import { signedPoints } from './range.js';

/* A subject whose decision is to remove it is not tested again: it has no
   next-test line, and the decision line says where the removal stands. */
export const REMOVING = ['retire', 'retire-pending'];
const isRemoving = (v) => REMOVING.includes(v);

export function verdictLine(v, removal, refMs) {
  if (v === null || v === undefined || v === '') return null;
  const key = String(v);
  const known = Object.prototype.hasOwnProperty.call(STRINGS.verdict, key);
  const text = known ? STRINGS.verdict[key] : STRINGS.verdictOther(clean(key));
  const r = removal && typeof removal === 'object' && Object.prototype.hasOwnProperty.call(STRINGS.removal, removal.state) ? STRINGS.removal[removal.state] : null;
  if (!r || !isRemoving(key)) return h('p', { class: 'meta' }, text);
  const since = parseTime(removal.since);
  const where = r.link ? link(removal.url, r.link) : null;
  // A merged removal replaces the decision line; any other state follows the plain one.
  const status = r.text(isFinite(since) ? fmtDay(since, refMs) : null);
  return h('p', { class: 'meta' }, removal.state === 'removed' ? [status] : [text, ' ', status], where ? [' ', where] : null);
}

export function nextText(nt, refMs, kind) {
  const n = nt && typeof nt === 'object' ? nt : {};
  if (typeof n.position === 'number' && isFinite(n.position)) return STRINGS.nextQueued(n.position, kind);
  if (isFinite(parseTime(n.due))) return STRINGS.nextDue(fmtDay(parseTime(n.due), refMs));
  return n.scheduled ? STRINGS.nextNone : STRINGS.nextUnscheduled;
}
export const nextLine = (nt, refMs, kind, verdict) => (isRemoving(verdict) ? null : h('p', { class: 'meta' }, nextText(nt, refMs, kind)));

export function stakesLine(st) {
  if (!st || typeof st !== 'object' || typeof st.reason !== 'string') return null;
  if (st.level === 'high') return h('p', { class: 'meta' }, STRINGS.stakesHigh(clean(st.reason)));
  if (st.level === 'none' && typeof st.covered_by === 'string') return h('p', { class: 'meta' }, STRINGS.stakesNone(clean(st.reason), clean(st.covered_by)));
  return null;
}

// Adam, 2026-11-07: the recorded runs the decision does not count, their
// list-price cost and the top reasons; nothing when `discarded_runs` is null
// (unknown) or empty.
export function discardedLine(d) {
  if (!d || typeof d !== 'object' || !Number.isInteger(d.total) || d.total <= 0) return null;
  const usd = typeof d.cost_usd === 'number' && isFinite(d.cost_usd) ? fmtUsd(d.cost_usd) : STRINGS.noValue;
  const rows = Object.entries(d.by_reason && typeof d.by_reason === 'object' ? d.by_reason : {})
    .filter(([, r]) => r && Number.isInteger(r.runs) && r.runs > 0)
    .sort((a, b) => b[1].runs - a[1].runs || (a[0] < b[0] ? -1 : 1))
    .slice(0, 3)
    .map(([k, r]) => (Object.prototype.hasOwnProperty.call(STRINGS.discardedReasons, k) ? STRINGS.discardedReasons[k] : clean(k)) + ' (' + r.runs + ')');
  const unknown = Number.isInteger(d.cost_unknown) ? d.cost_unknown : 0;
  return h('p', { class: 'meta' }, STRINGS.discarded(d.total, usd, unknown, rows.join(', ')));
}

export function usageLine(u, window, refMs) {
  if (!u || typeof u.invocations !== 'number' || !window) return null;
  return h('p', { class: 'meta' }, STRINGS.used(u.invocations, fmtUtcDay(parseTime(window.from), refMs), fmtUtcDay(parseTime(window.to), refMs)));
}

// #562: uses by which copy they loaded, counted from `copies.loaded`; nothing
// when `copies` is null (no census of copies: unknown, not zero).
export function copiesLine(c) {
  if (!c || !Array.isArray(c.loaded)) return null;
  const n = { match: 0, older: 0, unknown: 0 };
  for (const e of c.loaded) {
    if (!e || !Number.isInteger(e.invocations)) continue;
    const k = e.vs_main === 'current' || e.vs_main === 'in-window' ? 'match' : e.vs_main === 'older' ? 'older' : 'unknown';
    n[k] += e.invocations;
  }
  if (n.match + n.older + n.unknown === 0) return h('p', { class: 'meta' }, STRINGS.copiesNone);
  return h('p', { class: 'meta' }, STRINGS.copies(n.match, n.older, n.unknown));
}

export function chipSummary(items, mode) {
  const counts = {};
  items.forEach((i) => { counts[i.chip] = (counts[i.chip] || 0) + 1; });
  const parts = STRINGS.chipOrder.filter((k) => counts[k]).map((k) => counts[k] + ' ' + STRINGS.chips[k].toLowerCase());
  if (!parts.length) return null;
  return h('p', { class: 'summary-line' }, STRINGS.summaryCounts(parts.join(', ')));
}

/* Best first: the loop's keep, then early signs, trending toward removal,
   no difference, the test cannot tell, not enough data. */
const TABLE_RANK = ['helps', 'alone', 'early', 'worse', 'none', 'canttell', 'insufficient'];
/* The Next test column in a few words. */
function nextCell(nt, refMs, verdict) {
  if (isRemoving(verdict)) return STRINGS.nextCell.removing;
  const n = nt && typeof nt === 'object' ? nt : {};
  if (typeof n.position === 'number' && isFinite(n.position)) return STRINGS.nextCell.queued(n.position);
  if (isFinite(parseTime(n.due))) return STRINGS.nextCell.due(fmtDay(parseTime(n.due), refMs));
  return n.scheduled ? STRINGS.nextCell.none : STRINGS.nextCell.unscheduled;
}

/* One sortable row per skill or section. Skills show real-work
   uses, sections their size; each name opens its page. */
export function subjectTable(items, kind, refMs) {
  const guidance = kind === 'guidance';
  const uses = (it) => (it.raw.usage && Number.isInteger(it.raw.usage.invocations) ? it.raw.usage.invocations : -1);
  const gain = (it) => gainOf(it.pooled.all, guidance ? 'guidance' : 'skills');
  const rows = items.slice().sort((a, b) => TABLE_RANK.indexOf(a.chip) - TABLE_RANK.indexOf(b.chip) || (guidance ? 0 : uses(b) - uses(a)));
  return table([
    { label: STRINGS.colName, sort: (it) => it.name, cell: (it) => [navLink(hashFor(kind, it.id || it.name), clean(guidance ? it.raw.heading || it.id : it.name)), it.raw.private === true ? [' ', badge(STRINGS.privateBadge, 'private')] : null] },
    { label: STRINGS.colStatus, sort: (it) => TABLE_RANK.indexOf(it.chip), cell: (it) => chip(it.chip) },
    { label: STRINGS.colGain, num: true, sort: (it) => gain(it), cell: (it) => (gain(it) === null ? STRINGS.noValue : signedPoints(gain(it) * 100)) },
    { label: STRINGS.colRuns, num: true, sort: (it) => runsOf(it.pooled.all, guidance ? 'guidance' : 'skills'), cell: (it) => fmtCount(runsOf(it.pooled.all, guidance ? 'guidance' : 'skills')) },
    guidance ? { label: STRINGS.colSize, num: true, sort: (it) => it.bytes, cell: (it) => fmtCount(wordsFor(it.bytes)) }
      : { label: STRINGS.colUses, num: true, sort: uses, cell: (it) => (uses(it) < 0 ? STRINGS.noValue : fmtCount(uses(it))) },
    guidance ? { label: STRINGS.colPerKb, num: true, sort: (it) => gainPer100Words(it.pooled, it.bytes), cell: (it) => { const g = gainPer100Words(it.pooled, it.bytes); return g === null ? STRINGS.noValue : g.toFixed(1); } } : null,
    { label: STRINGS.colNext, sort: (it) => { const k = nextKey(it.raw.next_test); return k[0] * 1e14 + k[1]; }, cell: (it) => nextCell(it.raw.next_test, refMs, it.raw.verdict) },
    { label: STRINGS.colDecision, sort: (it) => it.raw.verdict || '', cell: (it) => STRINGS.verdictCell[it.raw.verdict || 'insufficient'] || clean(it.raw.verdict) }
  ].filter(Boolean), rows);
}
