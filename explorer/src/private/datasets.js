/* Reading the private dashboard's own datasets. Only the private entry
   imports this directory; explorer/test/run.js holds the public bundle to
   that. */

/* dashboard/build.py writes one placeholder row (this key field "none")
   instead of an empty list, because the Dashboard reads [] as "failed to
   load"; the page never shows it. */
export const PLACEHOLDER_KEY = {
  usage_rows: 'kind', usage_sources: 'key', run_stream: 'key', checkins: 'id', waiting: 'id',
  cost_benefit_weeks: 'week', half_built_issues: 'key'
};

/* rows(dash, id): the dataset's rows without placeholders, or null when it
   is missing, loading or failed, so the panel that reads it hides itself. */
export function rowsOf(dash, id) {
  let d;
  try { d = dash.data(id); } catch (e) { return null; }
  if (!d || d.status !== 'ok' || !Array.isArray(d.data)) return null;
  const k = PLACEHOLDER_KEY[id];
  return k ? d.data.filter((r) => r && r[k] !== 'none') : d.data.filter(Boolean);
}

/* The dataset's rows, or null when there are none to show. */
export function some(dash, id) {
  const r = rowsOf(dash, id);
  return r && r.length ? r : null;
}
