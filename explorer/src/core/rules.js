/* Rules. Every threshold the status chips use lives here. */

export const SCHEMA_VERSION = 1;
export const WINDOW_WEEKS = 26;          // pool runs from the last 26 weeks
export const MIN_PAIRED_RUNS = 5;        // the page's own rule for the whole-guidance headline only; the loop itself has no run minimum
export const HELPS_MIN_GAIN = 0.05;      // 5 percentage points better on at least one model
export const WORSE_TOLERANCE = -0.05;    // and never more than 5 points worse on any model
export const EPS = 1e-9;                 // float tolerance for the comparisons above
export const WEEK_MS = 7 * 24 * 3600 * 1000;

export const TIME_ZONE = 'America/New_York';

export const pts = (x) => Math.round(Math.abs(x) * 100);
/* The keep and removal levels when the data carries no policy; the page
   shows the data's own `policy.benefit_confidence`, `retire_confidence` and
   `max_runs_per_cell`. */
export const KEEP_AT = 0.80, REMOVE_AT = 0.90;
export const ordinal = (n) => { const t = n % 100, u = n % 10;
  return n + (t >= 11 && t <= 13 ? 'th' : u === 1 ? 'st' : u === 2 ? 'nd' : u === 3 ? 'rd' : 'th'); };
export const countWord = (n) => ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'][n] || String(n);
