/* Git hook checks from the document's `hooks`: one item per check, and the
   weekly totals the summary and impact views read. */
import { parseTime, weekKeyOf, dayKeyMs } from './format.js';

export const HOOK_RANK = ['earning', 'overridden-often', 'never-blocked', 'never-fires', 'never-ran'];

/* When a check began: the day it was made when the document lists it among
   the agent-made checks, else the first week it ran; null when neither. */
function sinceOf(doc, c) {
  const made = doc.agent_made && Array.isArray(doc.agent_made.items) ? doc.agent_made.items.find((i) => i && i.kind === 'check' && i.id === c.name) : null;
  const weeks = (Array.isArray(c.use) ? c.use : []).filter((u) => u && Number.isInteger(u.invocations) && u.invocations > 0).map((u) => dayKeyMs(u.week));
  // A first run in the data window's first week may be older than the data: unknown, not the window start.
  const from = doc.hooks && doc.hooks.window && typeof doc.hooks.window.from === 'string' ? dayKeyMs(mondayOf(dayKeyMs(doc.hooks.window.from))) : -Infinity;
  const first = Math.min(...weeks);
  const at = made ? parseTime(made.created) : first > from ? first : NaN;
  return isFinite(at) ? at : null;
}

/* What the loop does with a check next, and when: a check that has not
   blocked anything has until `weeks` weeks after it began to do so; after that it
   is a candidate for removal (nothing removes it by itself).
   {key: 'young'|'due'|'overridden'|'earning'|'unknown', at}. */
export function hookNext(it, weeks, refMs) {
  if (it.verdict === 'earning') return { key: 'earning', at: null };
  if (it.verdict === 'overridden-often') return { key: 'overridden', at: null };
  if (it.since === null) return { key: 'unknown', at: null };
  const at = it.since + weeks * 7 * 86400000;
  return { key: at > refMs ? 'young' : 'due', at };
}

export function hookItems(doc) {
  const h = doc && doc.hooks;
  const checks = h && Array.isArray(h.checks) ? h.checks : [];
  return checks.filter((c) => c && typeof c.name === 'string').map((c) => {
    const t = c.window_totals && typeof c.window_totals === 'object' ? c.window_totals : null;
    return { name: c.name, raw: c, where: c.where === 'repo' ? 'repo' : 'fleet', repo: typeof c.repo === 'string' ? c.repo : null,
      runs: t && Number.isInteger(t.invocations) ? t.invocations : null,
      runsCounted: t && Number.isInteger(t.invocations_counted) ? t.invocations_counted : (t && Number.isInteger(t.invocations) ? t.invocations : null),
      blocked: t ? t.blocked : null,
      overridden: t && Number.isInteger(t.overridden) ? t.overridden : null,
      overrideRate: t && typeof t.override_rate === 'number' ? t.override_rate : null,
      since: sinceOf(doc, c), measured: c.overrides_measured === true, verdict: typeof c.verdict === 'string' ? c.verdict : null,
      reason: typeof c.verdict_reason === 'string' ? c.verdict_reason : '',
      use: Array.isArray(c.use) ? c.use.filter((u) => u && typeof u.week === 'string') : [] };
  }).sort((a, b) => {
    const ra = HOOK_RANK.indexOf(a.verdict), rb = HOOK_RANK.indexOf(b.verdict);
    return (ra < 0 ? 9 : ra) - (rb < 0 ? 9 : rb) || (b.blocked || 0) - (a.blocked || 0) || (a.name < b.name ? -1 : 1);
  });
}

/* The Monday (YYYY-MM-DD, the data's own week key) of the week holding `ms`: the week label the
   usage producers use. */
export function mondayOf(ms) {
  return weekKeyOf(ms);
}

/* Whether the document counts cloud sessions' hook runs: true when
   `hooks.totals.cloud` is a list, false when the totals leave it out (no
   cloud records were read, so cloud is not counted, not zero), null with no
   totals at all. */
export function cloudCounted(doc) {
  const t = doc && doc.hooks && doc.hooks.totals;
  if (!t || typeof t !== 'object') return null;
  return Array.isArray(t.cloud);
}

/* Rows of hook use summed by week and surface: [{week, local:{runs,blocked}, ci:{...}, cloud:{...}}], newest first. */
export function hookWeeks(doc) {
  const t = doc && doc.hooks && doc.hooks.totals;
  if (!t || typeof t !== 'object') return [];
  const by = new Map();
  for (const surface of ['local', 'ci', 'cloud']) {
    for (const u of Array.isArray(t[surface]) ? t[surface] : []) {
      if (!u || typeof u.week !== 'string') continue;
      if (!by.has(u.week)) by.set(u.week, { week: u.week, local: { runs: 0, blocked: 0 }, ci: { runs: 0, blocked: 0 }, cloud: { runs: 0, blocked: 0 } });
      const cell = by.get(u.week)[surface];
      cell.runs += Number(u.invocations) || 0;
      cell.blocked += Number(u.blocked) || 0;
    }
  }
  return Array.from(by.values()).sort((a, b) => (a.week < b.week ? 1 : -1));
}

/* What the summary's hooks tile shows. Counts come in weekly totals only,
   so the headline is the last FULL week (never a partial week beside a full
   one) and the week in progress is shown apart, as "so far", with how many
   days it has run. {last, now, days, weeks: [{week, blocked, runs, partial}]
   oldest first (at most `n`), cloud: cloudCounted(doc)}, or null without
   hook totals or a document time. */
export function hookTile(doc, n) {
  if (!doc || !doc.hooks || !doc.hooks.totals) return null;
  const at = parseTime(doc.generated_at);
  if (!isFinite(at)) return null;
  const week = mondayOf(at);
  const day = 24 * 3600 * 1000;
  const rows = hookWeeks(doc);
  const sum = (r, k) => r.local[k] + r.ci[k] + r.cloud[k];
  const cell = (w) => {
    const r = rows.find((x) => x.week === w);
    return { week: w, blocked: r ? sum(r, 'blocked') : 0, runs: r ? sum(r, 'runs') : 0,
      local: r ? r.local.blocked : 0, ci: r ? r.ci.blocked : 0, cloud: r ? r.cloud.blocked : 0, partial: w === week };
  };
  // Weeks the counts cover start at the window's start: a week there with
  // no rows was measured as zero, not missing.
  const from = doc.hooks.window && typeof doc.hooks.window.from === 'string' ? mondayOf(Date.parse(doc.hooks.window.from + 'T00:00:00Z')) : null;
  const oldest = from || (rows.length ? rows[rows.length - 1].week : week);
  const weeks = [];
  for (let t = Date.parse(week + 'T00:00:00Z'), k = 0; k < (n || 6); t -= 7 * day, k++) {
    const w = mondayOf(t);
    if (w < oldest) break;
    weeks.unshift(cell(w));
  }
  const prev = mondayOf(Date.parse(week + 'T00:00:00Z') - 7 * day);
  return { last: prev >= oldest ? cell(prev) : null, now: cell(week),
    days: Math.min(7, Math.floor((at - Date.parse(week + 'T00:00:00Z')) / day) + 1),
    weeks, cloud: cloudCounted(doc) };
}
