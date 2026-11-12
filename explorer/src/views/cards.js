/* The lines a subject's page and the Skills and Guidance tables share, and the counts line above the table. */
import { STRINGS } from '../core/strings.js';
import { clean, parseTime, fmtDay, fmtUtcDay, wordsFor, fmtUsd, fmtGain, fmtCount } from '../core/format.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';
import { purposeOf, nextKey } from '../core/items.js';
import { gainOf, runsOf } from '../core/stats.js';
import { hashFor } from '../core/route.js';
import { navLink, table } from './bits.js';

export function verdictLine(v) {
  if (v === null || v === undefined || v === '') return null;
  const key = String(v);
  return h('p', { class: 'meta' }, Object.prototype.hasOwnProperty.call(STRINGS.verdict, key) ? STRINGS.verdict[key] : STRINGS.verdictOther(clean(key)));
}

export function nextText(nt, refMs, kind) {
  const n = nt && typeof nt === 'object' ? nt : {};
  if (typeof n.position === 'number' && isFinite(n.position)) return STRINGS.nextQueued(n.position, kind);
  if (isFinite(parseTime(n.due))) return STRINGS.nextDue(fmtDay(parseTime(n.due), refMs));
  return n.scheduled ? STRINGS.nextNone : STRINGS.nextUnscheduled;
}
export const nextLine = (nt, refMs, kind) => h('p', { class: 'meta' }, nextText(nt, refMs, kind));

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
const afterColon = (t) => { const x = t.replace(/^[^:]*: /, ''); return x.charAt(0).toUpperCase() + x.slice(1); };

/* One sortable row per skill or section. Skills show real-work
   uses, sections their size; each name opens its page. */
export function subjectTable(items, kind, refMs) {
  const guidance = kind === 'guidance';
  const uses = (it) => (it.raw.usage && Number.isInteger(it.raw.usage.invocations) ? it.raw.usage.invocations : -1);
  const gain = (it) => gainOf(it.pooled.all, guidance ? 'guidance' : 'skills');
  const rows = items.slice().sort((a, b) => TABLE_RANK.indexOf(a.chip) - TABLE_RANK.indexOf(b.chip) || (guidance ? 0 : uses(b) - uses(a)));
  return table([
    { label: STRINGS.colName, sort: (it) => it.name, cell: (it) => navLink(hashFor(kind, it.id || it.name), clean(guidance ? it.raw.heading || it.id : it.name)) },
    { label: STRINGS.colStatus, sort: (it) => TABLE_RANK.indexOf(it.chip), cell: (it) => chip(it.chip) },
    { label: STRINGS.colGain, num: true, sort: (it) => gain(it), cell: (it) => fmtGain(gain(it)) },
    { label: STRINGS.colRuns, num: true, sort: (it) => runsOf(it.pooled.all, guidance ? 'guidance' : 'skills'), cell: (it) => fmtCount(runsOf(it.pooled.all, guidance ? 'guidance' : 'skills')) },
    guidance ? { label: STRINGS.colSize, num: true, sort: (it) => it.bytes, cell: (it) => fmtCount(wordsFor(it.bytes)) }
      : { label: STRINGS.colUses, num: true, sort: uses, cell: (it) => (uses(it) < 0 ? STRINGS.noValue : fmtCount(uses(it))) },
    { label: STRINGS.colNext, sort: (it) => { const k = nextKey(it.raw.next_test); return k[0] * 1e14 + k[1]; }, cell: (it) => afterColon(nextText(it.raw.next_test, refMs, guidance ? 'section' : 'skill')) },
    { label: STRINGS.colDecision, sort: (it) => it.raw.verdict || '', cell: (it) => afterColon(it.raw.verdict ? (STRINGS.verdict[it.raw.verdict] || STRINGS.verdictOther(clean(it.raw.verdict))) : STRINGS.verdict.insufficient) }
  ], rows);
}
