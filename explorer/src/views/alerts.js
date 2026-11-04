/* Open alerts, and the fires-without-results line. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, parseTime, fmtDay } from '../core/format.js';
import { h, link } from '../core/h.js';

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

export function alertsView(doc, mode) {
  const want = mode === 'guidance' ? 'guidance' : 'skill';
  const alerts = (Array.isArray(doc.alerts) ? doc.alerts : []).filter((a) => a && a.subject === want);
  const f = doc.fires_without_results;
  const fires = f && Number.isInteger(f.without_results) && Number.isInteger(f.rejected) && (f.without_results || f.rejected) && typeof f.since === 'string'
    ? h('p', { class: 'note' }, STRINGS.firesLine(f.without_results, fmtDay(parseTime(f.since)), Array.isArray(f.sweeps) ? f.sweeps.length : 0, f.rejected)) : null;
  return h('section', null, h('h2', null, STRINGS.alertsHeading), fires,
    alerts.length ? h('ul', { class: 'plain' }, alerts.map((a) => {
      const kind = Object.prototype.hasOwnProperty.call(STRINGS.alertKinds, a.kind) ? STRINGS.alertKinds[a.kind] : clean(a.kind);
      const l = link(a.url, STRINGS.alertDetails);
      return h('li', null, h('strong', null, kind + ': ' + clean(a.name)), a.model ? ' (' + friendlyModel(a.model) + ')' : null,
        a.text ? ' ' + clean(a.text) : (alertText(a) ? ' ' + alertText(a) : null), l ? [' ', l] : null);
    })) : h('p', null, STRINGS.alertsNone));
}
