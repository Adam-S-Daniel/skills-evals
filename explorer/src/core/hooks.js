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
  const oldest = rows.length ? rows[rows.length - 1].week : week;
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
