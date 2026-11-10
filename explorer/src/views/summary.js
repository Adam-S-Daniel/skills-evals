/* Summary: the front page's headline tiles. */
import { STRINGS } from '../core/strings.js';
import { parseTime, fmtDateTime, fmtCount } from '../core/format.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';
import { skillItems, wholeGuidance } from '../core/items.js';
import { blockedThisWeek } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { term, defn } from '../core/terms.js';
import { tile, srcTip, panel } from './bits.js';
import { alertsView, firesFigures } from './alerts.js';
import { utilityView, fleetGroups, hasUtility } from './utility.js';
import { isTrending } from '../core/stats.js';

/* One line saying what each time on the page refers to. */
export function asOfLine(doc, refMs) {
  const newest = parseTime(doc.newest_run);
  return h('p', { class: 'src asof-line' }, defn('dataBuilt'), ' ' + fmtDateTime(refMs), ' \u00b7 ', defn('newestRun'), ' ' + (isFinite(newest) ? fmtDateTime(newest) : STRINGS.noRunsYet));
}

/* "7 help · 3 trending toward removal · ...": every skill's state, each a
   button that opens what it means, the untested ones included. */
export function skillStates(doc, tested) {
  const counts = {};
  tested.forEach((s) => { counts[s.chip] = (counts[s.chip] || 0) + 1; });
  const parts = STRINGS.chipOrder.filter((k) => counts[k]).map((k) => [counts[k] + ' ', term(STRINGS.chips[k].toLowerCase(), STRINGS.chipRules[k], { title: STRINGS.chips[k] })]);
  const listed = Array.isArray(doc.skills) ? doc.skills.filter(Boolean) : [];
  const testedNames = new Set(tested.map((s) => s.name));
  const rest = { skipped: 0, gap: 0 };
  listed.forEach((s) => { if (!testedNames.has(String(s.name)) && Object.prototype.hasOwnProperty.call(rest, s.status)) rest[s.status] += 1; });
  for (const k of Object.keys(rest)) {
    if (rest[k]) parts.push([rest[k] + ' ', term(STRINGS.skillStateExtra[k].toLowerCase(), STRINGS.skillStateDefs[k], { title: STRINGS.skillStateExtra[k] })]);
  }
  const out = [];
  parts.forEach((p, i) => { if (i) out.push(' \u00b7 '); out.push(p); });
  return out.length ? out : STRINGS.skillStatesAll;
}

export function summaryView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const src = STRINGS.srcDoc;
  const tip = srcTip(src, refMs);
  const tiles = [];
  const b = blockedThisWeek(doc);
  tiles.push(tile({ label: STRINGS.tileStopped, href: hashFor('hooks'), tip,
    value: b ? fmtCount(b.local + b.ci) : STRINGS.noValue,
    note: b ? STRINGS.tileStoppedNote(fmtCount(b.local), fmtCount(b.ci), b.week, b.prev ? fmtCount(b.prev.local) : '', b.prev ? fmtCount(b.prev.ci) : '', b.prev ? b.prev.week : '') : STRINGS.tileStoppedNone }));
  const skills = skillItems(doc);
  const tested = skills.filter((s) => s.raw.status === 'covered' || s.pooled.all.n > 0);
  tiles.push(tile({ label: STRINGS.tileHelped, href: hashFor('skills'), tip,
    value: fmtCount(tested.filter((s) => s.chip === 'helps').length),
    note: [STRINGS.tileHelpedNote(tested.length, Array.isArray(doc.skills) ? doc.skills.filter(Boolean).length : tested.length), ' ', skillStates(doc, tested)] }));
  const whole = wholeGuidance(doc);
  tiles.push(tile({ label: STRINGS.tileWhole, href: hashFor('guidance'), tip,
    value: chip(whole.chip, STRINGS.wholeRule), note: STRINGS.wholeAnswer[whole.chip] }));
  // The alerts list below also carries the fires-without-results line, so
  // the tile counts it too.
  const alerts = Array.isArray(doc.alerts) ? doc.alerts.filter((a) => a && !isTrending(doc, a)) : [];
  const trending = (Array.isArray(doc.alerts) ? doc.alerts : []).filter((a) => isTrending(doc, a));
  const names = new Set(trending.map((a) => a.subject + ':' + a.name));
  tiles.push(tile({ label: STRINGS.tileAlerts, value: fmtCount(alerts.length + (firesFigures(doc) ? 1 : 0)), tip,
    note: STRINGS.tileAlertsNote + '.' + (names.size ? STRINGS.tileTrendingNote(names.size) : '') }));
  const extra = ctx && ctx.ext && ctx.ext.summaryTiles ? ctx.ext.summaryTiles(ctx) : [];
  return h('div', null,
    h('p', { class: 'lead' }, STRINGS.summaryLead),
    asOfLine(doc, refMs),
    h('div', { class: 'tiles' }, tiles, extra),
    hasUtility(doc) ? panel(STRINGS.utilityFleetHeading, utilityView(fleetGroups(doc), refMs)) : null,
    ctx && ctx.ext && ctx.ext.summaryPanels ? ctx.ext.summaryPanels(ctx, doc) : null,
    alertsView(doc, 'all'));
}
