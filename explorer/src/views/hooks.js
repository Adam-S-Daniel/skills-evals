/* Git hooks: one row per check, and a page per check. */
import { STRINGS } from '../core/strings.js';
import { HOOK_GLOSSES } from '../core/glosses.js';
import { clean, parseTime, fmtCount, fmtDayKey, fmtWeekStart, fmtDay } from '../core/format.js';
import { h, link } from '../core/h.js';
import { hookItems, hookNext, cloudCounted } from '../core/hooks.js';
import { hashFor } from '../core/route.js';
import { table, srcLine, navLink, panel, badge, rangeLine, srcLineFor } from './bits.js';
import { weekChart } from './weekchart.js';

const pct = (x) => Math.round(x * 100) + '%';
/* The window's weeks from the data (evals/hook-policy.yml), or null. */
const weeksOf = (w) => (Number.isInteger(w.weeks) && w.weeks > 0 ? w.weeks : null);

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

/* The next step for a check, with its date in Eastern time. */
export function nextStep(it, weeks, refMs) {
  const n = hookNext(it, weeks, refMs);
  return STRINGS.hookNext[n.key](n.at === null ? null : fmtDay(n.at, refMs), weeks);
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
  // Overrides are not counted for any check yet: drop the column of
  // "not counted" cells and say so once under the table.
  const anyMeasured = items.some((it) => it.measured);
  const rows = table([
    { label: STRINGS.colCheck, sort: (it) => it.name, cell: (it) => navLink(hashFor('hooks', it.name), clean(it.name)) },
    { label: STRINGS.colWhere, sort: (it) => it.where, cell: where },
    { label: STRINGS.colRunsWindow(weeksOf(w)), num: true, sort: (it) => (it.runs !== null ? it.runs : it.runsCounted), cell: runsCell },
    { label: STRINGS.colBlocked, num: true, sort: (it) => it.blocked, cell: blockedCell },
    anyMeasured ? { label: STRINGS.colOverrides, num: true, sort: (it) => (it.measured ? it.overridden : -1), cell: overrides } : null,
    { label: STRINGS.colVerdictShort, sort: (it) => it.verdict || '', cell: hookVerdict },
    { label: STRINGS.colSince, sort: (it) => it.since, cell: (it) => (it.since === null ? STRINGS.noValue : fmtDay(it.since, refMs)) },
    { label: STRINGS.colNextStep, sort: (it) => (hookNext(it, weeksOf(w), refMs).at || 0), cell: (it) => nextStep(it, weeksOf(w), refMs) }
  ].filter(Boolean), items, { cls: 'hooks' });
  const policy = hk.policy || {};
  return h('section', { class: 'block' }, h('h2', null, STRINGS.hooksHeading),
    rangeLine(doc),
    w.from ? h('p', { class: 'note' }, STRINGS.hooksNote(w.weeks, fmtDayKey(w.from, refMs), fmtDayKey(w.to, refMs))) : null,
    cloudNote(doc),
    typeof policy.max_override_rate === 'number' ? h('p', { class: 'note' }, STRINGS.hookRule(pct(policy.max_override_rate), weeksOf(w))) : null,
    items.length ? rows : h('p', null, STRINGS.hooksNone),
    items.length ? h('p', { class: 'note' }, STRINGS.hookRunsNote) : null,
    items.length && !anyMeasured ? h('p', { class: 'note' }, STRINGS.hookOverridesNote) : null,
    Number.isInteger(hk.unlisted) && hk.unlisted > 0 ? h('p', { class: 'note' }, STRINGS.hookUnlisted(hk.unlisted)) : null,
    hk.private_repos_shown ? h('p', { class: 'note' }, STRINGS.hookPrivateFold) : null);
}

/* Whether cloud Claude Code sessions are in the counts, said wherever hook
   counts appear; null when the document has no hook totals. */
export function cloudNote(doc) {
  const c = cloudCounted(doc);
  if (c === null) return null;
  const from = doc.hooks && typeof doc.hooks.cloud_from === 'string' ? fmtDayKey(doc.hooks.cloud_from) : null;
  return h('p', { class: 'note' }, c ? STRINGS.hooksCloudFrom(from) : STRINGS.hooksCloudNotLong);
}

/* One check's weeks, oldest first, summed over repos. */
export function checkWeeks(it) {
  const by = new Map();
  for (const u of it.use) {
    if (!by.has(u.week)) by.set(u.week, { week: u.week, localRuns: 0, localBlocked: 0, ciRuns: 0, ciBlocked: 0, cloudRuns: 0, cloudBlocked: 0, ciUnknown: false, overridden: null });
    const r = by.get(u.week);
    const s = u.surface === 'ci' || u.surface === 'cloud' ? u.surface : 'local';
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

/* What the check's window totals hold beyond its published rows: the
   private repos the data counts but does not list (too few to show as a
   row), or null when nothing is held back. */
export function hiddenPrivate(it, w) {
  const t = it.raw.window_totals;
  if (!t || typeof t !== 'object' || !w || typeof w.from !== 'string') return null;
  let runs = 0, blocked = 0;
  for (const u of it.use) {
    if (u.week < w.from) continue;
    if (Number.isInteger(u.invocations)) runs += u.invocations;
    blocked += Number(u.blocked) || 0;
  }
  const r = Number.isInteger(t.invocations_counted) ? t.invocations_counted - runs : 0;
  const b = Number.isInteger(t.blocked) ? t.blocked - blocked : 0;
  return r > 0 || b > 0 ? { runs: Math.max(r, 0), blocked: Math.max(b, 0) } : null;
}

export function hookPage(doc, name, ctx) {
  const refMs = parseTime(doc.generated_at);
  const it = hookItems(doc).find((x) => x.name === name);
  const back = h('p', { class: 'back' }, navLink(hashFor('hooks'), STRINGS.back(STRINGS.hookBack)));
  if (!it) return h('div', null, back, h('p', null, STRINGS.hookNotFound));
  const weeks = checkWeeks(it);
  const cloud = cloudCounted(doc) === true;
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
  const hidden = hiddenPrivate(it, doc.hooks && doc.hooks.window);
  return h('div', null, back,
    h('section', { class: 'block subject' },
      h('div', { class: 'subject-head' }, h('h2', { class: 'title' }, clean(it.name)), hookVerdict(it)),
      rangeLine(doc),
      h('h3', null, STRINGS.hookEnforcesHeading), h('p', null, gloss, src ? [' (', src, ')'] : null),
      h('p', { class: 'meta' }, STRINGS.hookWhereLine(it.where, it.repo ? clean(it.repo) : null)),
      h('h3', null, STRINGS.verdictHeading),
      h('p', null, hookVerdict(it), ' ', clean(it.reason)),
      h('p', { class: 'meta' }, STRINGS.colRuns + ': ', runsCell(it), '. '
        + STRINGS.colBlocked + ': ' + blockedCell(it) + '. ' + STRINGS.colOverrides + ': ',
        overrides(it), '.'),
      it.measured ? null : h('p', { class: 'note' }, STRINGS.hookOverridesNote),
      hidden ? h('p', { class: 'note' }, STRINGS.hookPrivateHidden(fmtCount(hidden.runs), fmtCount(hidden.blocked))) : null),
    panel(STRINGS.hookByWeek, weeks.length ? [
      weekChart(weeks.map((w) => ({ label: fmtDayKey(w.week, refMs), short: fmtDayKey(w.week, refMs), a: w.localBlocked + (cloud ? w.cloudBlocked : 0), b: w.ciBlocked })),
        [cloud ? STRINGS.colLocalCloudBlocked : STRINGS.colLocalBlocked, STRINGS.colCiBlocked], STRINGS.hookByWeek, STRINGS.weekTitles.hooks, [STRINGS.weekDefs.local, STRINGS.weekDefs.ci]),
      table([
        { label: STRINGS.colWeek, sort: (w) => w.week, cell: (w) => fmtWeekStart(w.week, refMs) },
        { label: STRINGS.colLocalRuns, num: true, sort: (w) => w.localRuns, cell: (w) => fmtCount(w.localRuns) },
        { label: STRINGS.colLocalBlocked, num: true, sort: (w) => w.localBlocked, cell: (w) => fmtCount(w.localBlocked) },
        { label: STRINGS.colCiRuns, num: true, sort: (w) => (w.ciRuns === null ? -1 : w.ciRuns), cell: (w) => (w.ciRuns === null ? STRINGS.runsNotCounted : fmtCount(w.ciRuns)) },
        { label: STRINGS.colCiBlocked, num: true, sort: (w) => w.ciBlocked, cell: (w) => fmtCount(w.ciBlocked) },
        cloud ? { label: STRINGS.colCloudRuns, num: true, sort: (w) => w.cloudRuns, cell: (w) => fmtCount(w.cloudRuns) } : null,
        cloud ? { label: STRINGS.colCloudBlocked, num: true, sort: (w) => w.cloudBlocked, cell: (w) => fmtCount(w.cloudBlocked) } : null,
        { label: STRINGS.colOverrides, num: true, sort: (w) => w.overridden, cell: (w) => (it.measured && w.overridden !== null ? fmtCount(w.overridden) : STRINGS.overridesNotCounted) }
      ].filter(Boolean), weeks.slice().reverse()), cloudNote(doc)] : null),
    panel(STRINGS.hookByRepo, byRepo.size ? table([
      { label: STRINGS.colRepo, sort: (r) => r.repo, cell: (r) => clean(r.repo) },
      { label: STRINGS.colSurface, sort: (r) => r.surface, cell: (r) => r.surface },
      { label: STRINGS.colRuns, num: true, sort: (r) => (r.runs === null ? -1 : r.runs), cell: (r) => (r.runs === null ? STRINGS.runsNotCounted : fmtCount(r.runs)) },
      { label: STRINGS.colBlocked, num: true, sort: (r) => r.blocked, cell: (r) => fmtCount(r.blocked) }
    ], Array.from(byRepo.values()).sort((a, b) => (b.runs === null ? -1 : b.runs) - (a.runs === null ? -1 : a.runs) || b.blocked - a.blocked)) : null),
    extra);
}
