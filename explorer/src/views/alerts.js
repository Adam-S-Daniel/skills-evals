/* Open alerts, and the fires-without-results line. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, parseTime, fmtDay, roundDecimals } from '../core/format.js';
import { h, link } from '../core/h.js';
import { defn, skillTerm, sectionTerm } from '../core/terms.js';
import { trendingView } from './trending.js';
import { isTrending, alertKindLabel } from '../core/stats.js';

// The sentence for an alert that carries fields instead of `text` (#545);
// null when it has neither, so the label stands alone.
export function alertText(a) {
  if (a.kind === 'context-drift' && typeof a.drift_since === 'string') {
    return STRINGS.alertDrift(clean(a.fixture), clean(a.repository), fmtDay(parseTime(a.drift_since)));
  }
  if (a.kind === 'loaded-copy' && typeof a.loaded === 'string' && typeof a.main === 'string') {
    return STRINGS.alertCopy(a.surface, clean(a.loaded), clean(a.main));
  }
  return null;
}

/* Whether the document reports fires worth a line, and the figures for it. */
export function firesFigures(doc) {
  const f = doc.fires_without_results;
  if (!f || !Number.isInteger(f.without_results) || !Number.isInteger(f.rejected) || !(f.without_results || f.rejected) || typeof f.since !== 'string') return null;
  return { n: f.without_results, rejected: f.rejected, total: Number.isInteger(f.counted) ? f.counted : null,
    day: fmtDay(parseTime(f.since)), sweeps: Array.isArray(f.sweeps) ? f.sweeps.length : 0 };
}

/* The fires line with "fire" and "sweep" as definition buttons; its text is
   STRINGS.firesLine's. */
export function firesNode(x) {
  const P = STRINGS.firesParts;
  const of = x.total === null ? '' : ' of ' + x.total;
  const many = x.total === null ? x.n !== 1 : x.total !== 1;
  return h('p', { class: 'note' }, x.n + of + ' ', defn('fire', many ? P.fires : P.fire), ' since ' + x.day + ' produced no results (' + x.sweeps + ' ',
    defn('sweep', x.sweeps === 1 ? P.sweep : P.sweeps), '); ' + x.rejected + of + ' produced results that did not validate.');
}

export function alertsView(doc, mode, folded) {
  const want = mode === 'guidance' ? 'guidance' : 'skill';
  // A regression on an undecided subject is "trending toward removal", a
  // table of its own; on a decided one it is listed here (isTrending).
  const alerts = (Array.isArray(doc.alerts) ? doc.alerts : []).filter((a) => a && !isTrending(doc, a) && (mode === 'all' || a.subject === want));
  const x = firesFigures(doc);
  const trending = trendingView(doc, mode, folded);
  return h('div', null, trending, h('section', null, h('h2', null, STRINGS.alertsHeading), x ? firesNode(x) : null,
    alerts.length ? (folded ? (ul) => h('details', { class: 'history' }, h('summary', null, STRINGS.alertsShow(alerts.length)), ul) : (ul) => ul)(h('ul', { class: 'plain' }, alerts.map((a) => {
      const kind = clean(alertKindLabel(doc, a));
      const l = link(a.url, STRINGS.alertDetails);
      return h('li', null, h('strong', null, kind + ': ', a.subject === 'guidance' ? sectionTerm(a.name, clean(a.name)) : skillTerm(a.name, clean(a.name))), a.model ? ' (' + friendlyModel(a.model) + ')' : null,
        a.text ? ' ' + clean(roundDecimals(a.text)) : (alertText(a) ? ' ' + alertText(a) : null), l ? [' ', l] : null);
    }))) : h('p', null, x || trending ? STRINGS.alertsNoneOther : STRINGS.alertsNone)));
}
