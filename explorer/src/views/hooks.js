/* Git hooks: one row per check, and a page per check. */
import { STRINGS } from '../core/strings.js';
import { HOOK_GLOSSES } from '../core/glosses.js';
import { clean, parseTime, fmtCount, fmtUtcDay } from '../core/format.js';
import { h, link } from '../core/h.js';
import { hookItems } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { table, srcLine, navLink, panel, badge } from './bits.js';
import { weekChart } from './weekchart.js';

const pct = (x) => Math.round(x * 100) + '%';

/* The Runs cell: the count, or what is counted when CI's share is not. */
function runsCell(it) {
  if (it.runs !== null) return fmtCount(it.runs);
  if (it.runsCounted) return STRINGS.runsPartial(it.runsCounted);
  return h('span', { class: 'muted' }, STRINGS.runsNotCounted);
}

/* "4 of 30 runs" when the runs are counted, else the plain block count. */
function blockedCell(it) {
  if (it.blocked === null) return STRINGS.noValue;
  return it.runs !== null && it.runs > 0 ? STRINGS.blockedOf(it.blocked, it.runs) : fmtCount(it.blocked);
}

export function hookVerdict(it) {
  const label = it.verdict && Object.prototype.hasOwnProperty.call(STRINGS.hookVerdicts, it.verdict) ? STRINGS.hookVerdicts[it.verdict] : STRINGS.hookVerdictNone;
  return badge(label, 'hv ' + (it.verdict || 'none'));
}

function overrides(it) {
  if (!it.measured) return h('span', { class: 'muted', title: STRINGS.hookOverridesNote }, STRINGS.overridesNotCounted);
  return fmtCount(it.overridden || 0) + (it.overrideRate !== null ? ' (' + pct(it.overrideRate) + ')' : '');
}

function where(it) {
  return STRINGS.hookWhere[it.where];
}

export function hooksList(doc) {
  const refMs = parseTime(doc.generated_at);
  const hk = doc.hooks;
  if (!hk || typeof hk !== 'object') return h('section', { class: 'block' }, h('h2', null, STRINGS.hooksHeading), h('p', null, STRINGS.hooksNone));
  const items = hookItems(doc);
  const w = hk.window || {};
  const day = (d) => fmtUtcDay(Date.parse(d + 'T00:00:00Z'), refMs);
  // Overrides are not counted for any check yet: drop the column of
  // "not counted" cells and say so once under the table.
  const anyMeasured = items.some((it) => it.measured);
  const rows = table([
    { label: STRINGS.colCheck, sort: (it) => it.name, cell: (it) => navLink(hashFor('hooks', it.name), clean(it.name)) },
    { label: STRINGS.colWhere, sort: (it) => it.where, cell: where },
    { label: STRINGS.colRunsWindow(w.weeks || 8), num: true, sort: (it) => (it.runs !== null ? it.runs : it.runsCounted), cell: runsCell },
    { label: STRINGS.colBlocked, num: true, sort: (it) => it.blocked, cell: blockedCell },
    anyMeasured ? { label: STRINGS.colOverrides, num: true, sort: (it) => (it.measured ? it.overridden : -1), cell: overrides } : null,
    { label: STRINGS.colVerdictShort, sort: (it) => it.verdict || '', cell: hookVerdict }
  ].filter(Boolean), items, { cls: 'hooks' });
  const policy = hk.policy || {};
  return h('section', { class: 'block' }, h('h2', null, STRINGS.hooksHeading),
    srcLine(STRINGS.srcDoc, refMs),
    w.from ? h('p', { class: 'note' }, STRINGS.hooksNote(w.weeks, day(w.from), day(w.to))) : null,
    typeof policy.max_override_rate === 'number' ? h('p', { class: 'note' }, STRINGS.hookRule(pct(policy.max_override_rate), w.weeks || 8)) : null,
    items.length ? rows : h('p', null, STRINGS.hooksNone),
    items.length ? h('p', { class: 'note' }, STRINGS.hookRunsNote) : null,
    items.length && !anyMeasured ? h('p', { class: 'note' }, STRINGS.hookOverridesNote) : null,
    Number.isInteger(hk.unlisted) && hk.unlisted > 0 ? h('p', { class: 'note' }, STRINGS.hookUnlisted(hk.unlisted)) : null,
    hk.private_repos_shown ? h('p', { class: 'note' }, STRINGS.hookPrivateFold) : null);
}

/* One check's weeks, oldest first, summed over repos. */
export function checkWeeks(it) {
  const by = new Map();
  for (const u of it.use) {
    if (!by.has(u.week)) by.set(u.week, { week: u.week, localRuns: 0, localBlocked: 0, ciRuns: 0, ciBlocked: 0, ciUnknown: false, overridden: null });
    const r = by.get(u.week);
    const s = u.surface === 'ci' ? 'ci' : 'local';
    // A null count is unknown, not zero: the sum stays unknown.
    if (Number.isInteger(u.invocations)) r[s + 'Runs'] += u.invocations; else r[s + 'Unknown'] = true;
    r[s + 'Blocked'] += Number(u.blocked) || 0;
    if (Number.isInteger(u.overridden)) r.overridden = (r.overridden || 0) + u.overridden;
  }
  const out = Array.from(by.values());
  // A week with a CI block but no CI run count has unknown CI runs; one with
  // neither has none to show either, as CI rows exist only for red runs.
  for (const r of out) r.ciRuns = r.ciUnknown || !r.ciRuns ? null : r.ciRuns;
  return out.sort((a, b) => (a.week < b.week ? -1 : 1));
}

export function hookPage(doc, name, ctx) {
  const refMs = parseTime(doc.generated_at);
  const it = hookItems(doc).find((x) => x.name === name);
  const back = h('p', { class: 'back' }, navLink(hashFor('hooks'), STRINGS.back(STRINGS.hookBack)));
  if (!it) return h('div', null, back, h('p', null, STRINGS.hookNotFound));
  const day = (d) => fmtUtcDay(Date.parse(d + 'T00:00:00Z'), refMs);
  const weeks = checkWeeks(it);
  const gloss = Object.prototype.hasOwnProperty.call(HOOK_GLOSSES, it.name) ? HOOK_GLOSSES[it.name] : STRINGS.hookEnforcesMissing;
  const src = link(it.raw.source_url, STRINGS.hookSourceLink);
  const byRepo = new Map();
  for (const u of it.use) {
    const k = (u.repo || STRINGS.unknown) + '|' + u.surface;
    if (!byRepo.has(k)) byRepo.set(k, { repo: u.repo || STRINGS.unknown, surface: u.surface, runs: 0, blocked: 0 });
    const r = byRepo.get(k);
    r.runs = r.runs === null || !Number.isInteger(u.invocations) ? null : r.runs + u.invocations;
    r.blocked += Number(u.blocked) || 0;
  }
  const extra = ctx && ctx.ext && ctx.ext.hookPage ? ctx.ext.hookPage(ctx, it) : null;
  return h('div', null, back,
    h('section', { class: 'block subject' },
      h('div', { class: 'subject-head' }, h('h2', { class: 'title' }, clean(it.name)), hookVerdict(it)),
      srcLine(STRINGS.srcDoc, refMs),
      h('h3', null, STRINGS.hookEnforcesHeading), h('p', null, gloss, src ? [' (', src, ')'] : null),
      h('p', { class: 'meta' }, STRINGS.hookWhereLine(it.where, it.repo ? clean(it.repo) : null)),
      h('h3', null, STRINGS.verdictHeading),
      h('p', null, hookVerdict(it), ' ', clean(it.reason)),
      h('p', { class: 'meta' }, STRINGS.colRuns + ': ', runsCell(it), '. '
        + STRINGS.colBlocked + ': ' + blockedCell(it) + '. ' + STRINGS.colOverrides + ': ',
        overrides(it), '.'),
      it.measured ? null : h('p', { class: 'note' }, STRINGS.hookOverridesNote)),
    panel(STRINGS.hookByWeek, weeks.length ? [
      weekChart(weeks.map((w) => ({ label: day(w.week), short: day(w.week), a: w.localBlocked, b: w.ciBlocked })),
        [STRINGS.colLocalBlocked, STRINGS.colCiBlocked], STRINGS.hookByWeek, STRINGS.weekTitles.hooks, [STRINGS.weekDefs.local, STRINGS.weekDefs.ci]),
      table([
        { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => day(w.week) },
        { label: STRINGS.colLocalRuns, num: true, sort: (w) => w.localRuns, cell: (w) => fmtCount(w.localRuns) },
        { label: STRINGS.colLocalBlocked, num: true, sort: (w) => w.localBlocked, cell: (w) => fmtCount(w.localBlocked) },
        { label: STRINGS.colCiRuns, num: true, sort: (w) => (w.ciRuns === null ? -1 : w.ciRuns), cell: (w) => (w.ciRuns === null ? STRINGS.runsNotCounted : fmtCount(w.ciRuns)) },
        { label: STRINGS.colCiBlocked, num: true, sort: (w) => w.ciBlocked, cell: (w) => fmtCount(w.ciBlocked) },
        { label: STRINGS.colOverrides, num: true, sort: (w) => w.overridden, cell: (w) => (it.measured && w.overridden !== null ? fmtCount(w.overridden) : STRINGS.overridesNotCounted) }
      ], weeks.slice().reverse())] : null),
    panel(STRINGS.hookByRepo, byRepo.size ? table([
      { label: STRINGS.colRepo, sort: (r) => r.repo, cell: (r) => clean(r.repo) },
      { label: STRINGS.colSurface, sort: (r) => r.surface, cell: (r) => r.surface },
      { label: STRINGS.colRuns, num: true, sort: (r) => (r.runs === null ? -1 : r.runs), cell: (r) => (r.runs === null ? STRINGS.runsNotCounted : fmtCount(r.runs)) },
      { label: STRINGS.colBlocked, num: true, sort: (r) => r.blocked, cell: (r) => fmtCount(r.blocked) }
    ], Array.from(byRepo.values()).sort((a, b) => (b.runs === null ? -1 : b.runs) - (a.runs === null ? -1 : a.runs) || b.blocked - a.blocked)) : null),
    extra);
}
