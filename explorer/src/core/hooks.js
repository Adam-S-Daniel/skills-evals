/* Git hook checks from the document's `hooks`: one item per check, and the
   weekly totals the summary and impact views read. */
import { parseTime } from './format.js';

export const HOOK_RANK = ['earning', 'overridden-often', 'never-blocked', 'never-fires', 'never-ran'];

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
      measured: c.overrides_measured === true, verdict: typeof c.verdict === 'string' ? c.verdict : null,
      reason: typeof c.verdict_reason === 'string' ? c.verdict_reason : '',
      use: Array.isArray(c.use) ? c.use.filter((u) => u && typeof u.week === 'string') : [] };
  }).sort((a, b) => {
    const ra = HOOK_RANK.indexOf(a.verdict), rb = HOOK_RANK.indexOf(b.verdict);
    return (ra < 0 ? 9 : ra) - (rb < 0 ? 9 : rb) || (b.blocked || 0) - (a.blocked || 0) || (a.name < b.name ? -1 : 1);
  });
}

/* The UTC Monday (YYYY-MM-DD) of the week holding `ms`: the week label the
   usage producers use. */
export function mondayOf(ms) {
  if (!isFinite(ms)) return null;
  const d = new Date(ms);
  const back = (d.getUTCDay() + 6) % 7;
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - back)).toISOString().slice(0, 10);
}

/* Rows of hook use summed by week and surface: [{week, local:{runs,blocked}, ci:{...}}], newest first. */
export function hookWeeks(doc) {
  const t = doc && doc.hooks && doc.hooks.totals;
  if (!t || typeof t !== 'object') return [];
  const by = new Map();
  for (const surface of ['local', 'ci']) {
    for (const u of Array.isArray(t[surface]) ? t[surface] : []) {
      if (!u || typeof u.week !== 'string') continue;
      if (!by.has(u.week)) by.set(u.week, { week: u.week, local: { runs: 0, blocked: 0 }, ci: { runs: 0, blocked: 0 } });
      const cell = by.get(u.week)[surface];
      cell.runs += Number(u.invocations) || 0;
      cell.blocked += Number(u.blocked) || 0;
    }
  }
  return Array.from(by.values()).sort((a, b) => (a.week < b.week ? 1 : -1));
}

/* Commits and pushes stopped in the week holding the document's time:
   {week, local, ci} or null when the document has no hook totals. */
export function blockedThisWeek(doc) {
  if (!doc || !doc.hooks || !doc.hooks.totals) return null;
  const week = mondayOf(parseTime(doc.generated_at));
  const weeks = hookWeeks(doc);
  const row = weeks.find((w) => w.week === week);
  // The data holds weekly totals only, so the week so far sits beside the
  // week before it; that one is shown only when the data reaches back to it.
  const before = isFinite(parseTime(doc.generated_at)) ? mondayOf(parseTime(doc.generated_at) - 7 * 24 * 3600 * 1000) : null;
  const prevRow = weeks.find((w) => w.week === before);
  const reaches = weeks.some((w) => w.week <= before);
  return { week, local: row ? row.local.blocked : 0, ci: row ? row.ci.blocked : 0,
    prev: reaches ? { week: before, local: prevRow ? prevRow.local.blocked : 0, ci: prevRow ? prevRow.ci.blocked : 0 } : null };
}
