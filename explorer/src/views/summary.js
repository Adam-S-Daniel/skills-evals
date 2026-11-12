/* Summary: the front page's headline tiles. */
import { STRINGS } from '../core/strings.js';
import { parseTime, fmtDateTime, fmtCount, fmtUtcDay } from '../core/format.js';
import { h } from '../core/h.js';
import { chip } from '../core/charts.js';
import { skillItems, sectionItems, wholeGuidance } from '../core/items.js';
import { hookTile } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { term, defn } from '../core/terms.js';
import { tile, srcTip, panel, blockMs, BLOCKS } from './bits.js';
import { alertsView, firesFigures } from './alerts.js';
import { trendingView } from './trending.js';
import { utilityView, fleetGroups, hasUtility } from './utility.js';
import { isTrending } from '../core/stats.js';

/* One line saying what each time on the page refers to. */
export function asOfLine(doc, refMs) {
  const newest = parseTime(doc.newest_run);
  const reads = BLOCKS.map((k) => blockMs(doc, k)).filter((m) => isFinite(m));
  const lo = Math.min.apply(null, reads), hi = Math.max.apply(null, reads);
  return h('p', { class: 'src asof-line' }, defn('dataBuilt'), ' ' + fmtDateTime(refMs), ' \u00b7 ', defn('newestRun'), ' ' + (isFinite(newest) ? fmtDateTime(newest) : STRINGS.noRunsYet),
    reads.length && fmtDateTime(lo) !== fmtDateTime(hi) ? ' \u00b7 ' + STRINGS.srcRange(fmtDateTime(lo), fmtDateTime(hi)) : null);
}

/* Every skill's state, counted: [{key, n, label}] in chip order, then the
   untested ones (left out on purpose, not yet tested). */
export function skillStateCounts(doc, tested) {
  const counts = {};
  tested.forEach((s) => { counts[s.chip] = (counts[s.chip] || 0) + 1; });
  const out = STRINGS.chipOrder.filter((k) => counts[k]).map((k) => ({ key: k, n: counts[k], label: STRINGS.chips[k], rule: STRINGS.chipRules[k] }));
  const listed = Array.isArray(doc.skills) ? doc.skills.filter(Boolean) : [];
  const testedNames = new Set(tested.map((s) => s.name));
  const rest = { skipped: 0, gap: 0 };
  listed.forEach((s) => { if (!testedNames.has(String(s.name)) && Object.prototype.hasOwnProperty.call(rest, s.status)) rest[s.status] += 1; });
  for (const k of Object.keys(rest)) {
    if (rest[k]) out.push({ key: k, n: rest[k], label: STRINGS.skillStateExtra[k], rule: STRINGS.skillStateDefs[k] });
  }
  return out;
}

/* A bar split by state, then a legend whose names are definition buttons. */
export function stateBar(parts, aria) {
  const total = parts.reduce((a, p) => a + p.n, 0);
  if (!total) return null;
  return h('span', { class: 'statebar' },
    h('span', { class: 'sbar', role: 'img', 'aria-label': aria }, parts.map((p) =>
      h('span', { class: 'sb ' + p.key, style: 'flex-grow:' + p.n }))),
    h('span', { class: 'legend-mini' }, parts.map((p) =>
      h('span', { class: 'li' }, h('span', { class: 'sw ' + p.key, 'aria-hidden': 'true' }), h('b', null, fmtCount(p.n)), ' ',
        term(p.label.toLowerCase(), p.rule, { title: p.label })))));
}

/* Blocked commits and pushes by week, the week in progress drawn apart. */
function hookBars(t, refMs) {
  const top = Math.max(1, ...t.weeks.map((w) => w.blocked));
  return h('span', { class: 'weekbars', role: 'img', 'aria-label': STRINGS.hooksBarsAria(t.weeks.map((w) => fmtUtcDay(Date.parse(w.week), refMs) + ' ' + w.blocked + (w.partial ? ' ' + STRINGS.hooksSoFarWord : '')).join(', ')) },
    t.weeks.map((w) => h('span', { class: 'wk' + (w.partial ? ' partial' : '') },
      h('span', { class: 'wn' }, fmtCount(w.blocked)),
      // Square root, so one bad week does not flatten every other bar.
      h('span', { class: 'wb', style: 'height:' + (w.blocked ? Math.max(8, Math.round(100 * Math.sqrt(w.blocked / top))) : 0) + '%' }),
      h('span', { class: 'wd' }, w.partial ? STRINGS.hooksSoFarWord : fmtUtcDay(Date.parse(w.week), refMs)))));
}

function hooksTile(doc, tip, refMs) {
  const t = hookTile(doc, 6);
  if (!t) return tile({ label: STRINGS.tileHooks, href: hashFor('hooks'), tip, value: STRINGS.noValue, note: STRINGS.tileStoppedNone });
  const last = t.last;
  return tile({ label: STRINGS.tileHooks, href: hashFor('hooks'), tip,
    value: last ? fmtCount(last.blocked) : STRINGS.noValue,
    note: [
      h('span', { class: 'lede' }, last ? STRINGS.hooksLastWeek(fmtUtcDay(Date.parse(last.week), refMs), fmtCount(last.local), fmtCount(last.ci), t.cloud ? fmtCount(last.cloud) : null) : STRINGS.hooksNoFullWeek),
      hookBars(t, refMs),
      h('span', { class: 'fine' }, STRINGS.hooksSoFar(fmtCount(t.now.blocked), t.days), ' ', t.cloud ? null : STRINGS.hooksCloudNot)] });
}

function guidanceTile(doc, tip) {
  const whole = wholeGuidance(doc);
  const g = whole.pooled.all.gain;
  const secs = sectionItems(doc);
  const counts = {};
  secs.forEach((s) => { counts[s.chip] = (counts[s.chip] || 0) + 1; });
  const parts = STRINGS.chipOrder.filter((k) => counts[k]).map((k) => ({ key: k, n: counts[k], label: STRINGS.chips[k], rule: STRINGS.chipRules[k] }));
  const models = whole.pooled.models.length;
  return tile({ label: STRINGS.tileGuidance, href: hashFor('guidance'), tip,
    value: g === null || !isFinite(g) ? STRINGS.noValue : [(Math.round(g * 100) >= 0 ? '+' : '−') + Math.abs(Math.round(g * 100)), h('span', { class: 'unit' }, STRINGS.ptsUnit)],
    note: [
      h('span', { class: 'lede' }, chip(whole.chip, STRINGS.wholeRule), ' ', g === null || !isFinite(g) ? STRINGS.guidanceNoRuns : STRINGS.guidanceGainLine(fmtCount(whole.pooled.all.n), models)),
      stateBar(parts, STRINGS.sectionsBarAria(secs.length)),
      h('span', { class: 'fine' }, STRINGS.sectionsOf(secs.length))] });
}

export function summaryView(doc, ctx) {
  const refMs = parseTime(doc.generated_at);
  const src = STRINGS.srcDoc;
  const tip = srcTip(src, refMs);
  const priv = !!(ctx && ctx.ext);
  const tiles = [hooksTile(doc, tip, refMs)];
  const skills = skillItems(doc);
  const tested = skills.filter((s) => s.raw.status === 'covered' || s.pooled.all.n > 0);
  const states = skillStateCounts(doc, tested);
  const all = Array.isArray(doc.skills) ? doc.skills.filter(Boolean).length : tested.length;
  tiles.push(tile({ label: STRINGS.tileSkills, href: hashFor('skills'), tip,
    value: fmtCount(tested.filter((s) => s.chip === 'helps').length),
    note: [h('span', { class: 'lede' }, STRINGS.skillsHelpLine(tested.length)),
      stateBar(states, STRINGS.skillsBarAria(all)) || STRINGS.skillStatesAll,
      h('span', { class: 'fine' }, STRINGS.skillsOf(all))] }));
  tiles.push(guidanceTile(doc, tip));
  // Alerts are the owner's to act on, so only the private dashboard has the
  // tile, and it opens Needs you, where each one is listed.
  if (priv) {
    const alerts = Array.isArray(doc.alerts) ? doc.alerts.filter((a) => a && !isTrending(doc, a)) : [];
    // The same rows Needs you lists for them (attentionRows), so the counts match.
    tiles.push(tile({ label: STRINGS.tileAlerts, href: hashFor('needs'), tip,
      value: fmtCount(alerts.length + (firesFigures(doc) ? 1 : 0)), note: STRINGS.tileAlertsNote }));
  }
  const extra = priv && ctx.ext.summaryTiles ? ctx.ext.summaryTiles(ctx) : [];
  return h('div', null,
    h('p', { class: 'lead' }, STRINGS.summaryLead),
    asOfLine(doc, refMs),
    h('div', { class: 'tiles' }, tiles, extra),
    hasUtility(doc) ? panel(STRINGS.utilityFleetHeading, utilityView(fleetGroups(doc), refMs)) : null,
    priv && ctx.ext.summaryPanels ? ctx.ext.summaryPanels(ctx, doc) : null,
    priv ? alertsView(doc, 'all') : trendingView(doc, 'all'));
}
