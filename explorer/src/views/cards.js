/* Skill and section cards, and the counts line above them. */
import { STRINGS } from '../core/strings.js';
import { GLOSSES, GLOSS_MISSING } from '../core/glosses.js';
import { clean, parseTime, fmtDay, fmtUtcDay, wordsFor } from '../core/format.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';
import { purposeOf } from '../core/items.js';
import { hashFor } from '../core/route.js';
import { navLink, badge } from './bits.js';
import { trendChart } from './trend.js';
import { modelCharts, hasAlone, legendFor, hasData } from './models.js';
import { confidenceView } from './range.js';

export function verdictLine(v) {
  if (v === null || v === undefined || v === '') return null;
  const key = String(v);
  return h('p', { class: 'meta' }, Object.prototype.hasOwnProperty.call(STRINGS.verdict, key) ? STRINGS.verdict[key] : STRINGS.verdictOther(clean(key)));
}

export function nextLine(nt, refMs, kind) {
  const n = nt && typeof nt === 'object' ? nt : {};
  let text;
  if (typeof n.position === 'number' && isFinite(n.position)) text = STRINGS.nextQueued(n.position, kind);
  else if (isFinite(parseTime(n.due))) text = STRINGS.nextDue(fmtDay(parseTime(n.due), refMs));
  else text = n.scheduled ? STRINGS.nextNone : STRINGS.nextUnscheduled;
  return h('p', { class: 'meta' }, text);
}

export function stakesLine(st) {
  if (!st || typeof st !== 'object' || typeof st.reason !== 'string') return null;
  if (st.level === 'high') return h('p', { class: 'meta' }, STRINGS.stakesHigh(clean(st.reason)));
  if (st.level === 'none' && typeof st.covered_by === 'string') return h('p', { class: 'meta' }, STRINGS.stakesNone(clean(st.reason), clean(st.covered_by)));
  return null;
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

export function skillCard(it, refMs, doc) {
  return h('article', { class: 'card' },
    h('div', { class: 'head' }, h('h3', null, navLink(hashFor('skills', it.name), clean(it.name))), chip(it.chip),
      it.raw.private === true ? badge(STRINGS.privateBadge, 'private') : null),
    h('p', { class: 'gl' }, clean(purposeOf(it.raw.description) || STRINGS.purposeMissing)),
    usageLine(it.raw.usage, doc && doc.usage, refMs),
    copiesLine(it.raw.copies),
    nextLine(it.raw.next_test, refMs, 'skill'),
    stakesLine(it.raw.stakes),
    h('p', { class: 'sent' }, clean(it.sentence)),
    hasData(it.pooled) ? [legendFor('skills', it.pooled), modelCharts(it.pooled, 'skills'), trendChart(it.trend, refMs)] : null,
    confidenceView(it.raw.confidence, doc && doc.policy, 'skills'),
    verdictLine(it.raw.verdict));
}

export function sectionCard(it, refMs, doc) {
  const gloss = Object.prototype.hasOwnProperty.call(GLOSSES, it.id) ? GLOSSES[it.id] : GLOSS_MISSING;
  return h('article', { class: 'card' },
    h('div', { class: 'head' }, h('h3', null, navLink(hashFor('guidance', it.id), clean(it.raw.heading || it.id))), chip(it.chip)),
    h('p', { class: 'gl' }, gloss),
    h('p', { class: 'meta', style: 'margin:0 0 6px' }, STRINGS.size(wordsFor(it.bytes))),
    nextLine(it.raw.next_test, refMs, 'section'),
    stakesLine(it.raw.stakes),
    h('p', { class: 'sent' }, clean(it.sentence)),
    hasAlone(it.pooled) ? h('p', { class: 'meta' }, STRINGS.aloneShown) : null,
    hasData(it.pooled) ? [legendFor('guidance', it.pooled), modelCharts(it.pooled, 'guidance'), trendChart(it.trend, refMs)] : null,
    confidenceView(it.raw.confidence, doc && doc.policy, 'guidance'),
    verdictLine(it.raw.verdict));
}

export function chipSummary(items, mode) {
  const counts = {};
  items.forEach((i) => { counts[i.chip] = (counts[i.chip] || 0) + 1; });
  const parts = STRINGS.chipOrder.filter((k) => counts[k]).map((k) => counts[k] + ' ' + STRINGS.chips[k].toLowerCase());
  if (!parts.length) return null;
  return h('p', { class: 'summary-line' }, STRINGS.summaryCounts(parts.join(', ')));
}
