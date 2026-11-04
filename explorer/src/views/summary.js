/* Summary: the front page's headline tiles. */
import { STRINGS } from '../core/strings.js';
import { parseTime, fmtDateTime, fmtCount } from '../core/format.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';
import { skillItems, wholeGuidance } from '../core/items.js';
import { blockedThisWeek } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { tile, srcTip, srcLine } from './bits.js';
import { alertsView } from './alerts.js';

export function summaryView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const src = STRINGS.srcDoc;
  const tip = srcTip(src, refMs);
  const tiles = [];
  const b = blockedThisWeek(doc);
  tiles.push(tile({ label: STRINGS.tileStopped, href: hashFor('hooks'), tip,
    value: b ? fmtCount(b.local + b.ci) : STRINGS.noValue,
    note: b ? STRINGS.tileStoppedNote(fmtCount(b.local), fmtCount(b.ci), b.week) : STRINGS.tileStoppedNone }));
  const skills = skillItems(doc);
  const tested = skills.filter((s) => s.raw.status === 'covered' || s.pooled.all.n > 0);
  tiles.push(tile({ label: STRINGS.tileHelped, href: hashFor('skills'), tip,
    value: fmtCount(tested.filter((s) => s.chip === 'helps').length), note: STRINGS.tileHelpedNote(tested.length) }));
  const whole = wholeGuidance(doc);
  tiles.push(tile({ label: STRINGS.tileWhole, href: hashFor('guidance'), tip,
    value: chip(whole.chip, STRINGS.wholeRule), note: STRINGS.wholeAnswer[whole.chip] }));
  const newest = parseTime(doc.newest_run);
  tiles.push(tile({ label: STRINGS.tileAsOf, value: fmtDateTime(refMs), tip, small: true,
    note: STRINGS.tileNewest + ': ' + (isFinite(newest) ? fmtDateTime(newest) : STRINGS.noRunsYet) }));
  // The alerts list below also carries the fires-without-results line, so
  // the tile counts it too.
  const alerts = Array.isArray(doc.alerts) ? doc.alerts.filter(Boolean) : [];
  const f = doc.fires_without_results;
  const fires = f && Number.isInteger(f.without_results) && Number.isInteger(f.rejected) && (f.without_results || f.rejected) && typeof f.since === 'string' ? 1 : 0;
  tiles.push(tile({ label: STRINGS.tileAlerts, value: fmtCount(alerts.length + fires), tip, note: STRINGS.tileAlertsNote }));
  const extra = ctx && ctx.ext && ctx.ext.summaryTiles ? ctx.ext.summaryTiles(ctx) : [];
  return h('div', null,
    h('p', { class: 'lead' }, STRINGS.summaryLead),
    srcLine(src, refMs),
    h('div', { class: 'tiles' }, tiles, extra),
    alertsView(doc, 'all'));
}
