/* Run statistics: pooling, chips, sentences and weekly gains. */
import { WINDOW_WEEKS, MIN_PAIRED_RUNS, HELPS_MIN_GAIN, WORSE_TOLERANCE, EPS, WEEK_MS } from './rules.js';
import { STRINGS } from './strings.js';
import { friendlyModel, parseTime, fmtDay, fmtCount, wordsFor } from './format.js';

export function armOf(x) {
  if (!x || typeof x !== 'object') return null;
  const passed = Number(x.checks_passed), total = Number(x.checks_total), trials = Number(x.trials);
  if (!isFinite(passed) || !isFinite(total) || total <= 0) return null;
  const judge = (typeof x.judge_mean === 'number' && isFinite(x.judge_mean)) ? x.judge_mean : null;
  return { passed: passed, total: total, trials: isFinite(trials) ? trials : 0, judge: judge };
}

/* Normalize a run so both subjects share one shape:
   with/without = the compared pair; full/ablated = the ablation pair (guidance only). */
export function normRun(run, subject) {
  if (!run || typeof run !== 'object') return null;
  const at = parseTime(run.at);
  const base = { model: String(run.model || ''), at: at, fixture: run.fixture, cli: run.cli_version, url: run.report_url };
  if (subject === 'guidance') {
    const m = run.modes || {};
    return Object.assign(base, { with: armOf(m.section), without: armOf(m.none), full: armOf(m.full), ablated: armOf(m.full_minus_section) });
  }
  if (subject === 'whole') {
    const m = run.modes || {};
    return Object.assign(base, { with: armOf(m.full), without: armOf(m.none), full: null, ablated: null });
  }
  return Object.assign(base, { with: armOf(run.with), without: armOf(run.without), full: null, ablated: null });
}

export function inWindow(r, refMs) {
  return isFinite(r.at) && (!isFinite(refMs) || r.at >= refMs - WINDOW_WEEKS * WEEK_MS);
}

export function emptyAcc() { return { n: 0, wp: 0, wt: 0, op: 0, ot: 0, trials: 0, nAbl: 0, fp: 0, ft: 0, ap: 0, at: 0, trialsAbl: 0, lastAbl: NaN, last: NaN, wj: 0, wjn: 0, oj: 0, ojn: 0 }; }

export function addRun(acc, r) {
  if (r.with && r.without) {
    acc.n += 1; acc.wp += r.with.passed; acc.wt += r.with.total; acc.op += r.without.passed; acc.ot += r.without.total;
    acc.trials += r.with.trials;
    if (r.with.judge !== null && r.without.judge !== null) {
      const tw = r.with.trials || 1, to = r.without.trials || 1;
      acc.wj += r.with.judge * tw; acc.wjn += tw; acc.oj += r.without.judge * to; acc.ojn += to;
    }
    if (!(acc.last >= r.at)) acc.last = r.at;
  }
  if (r.full && r.ablated) {
    acc.nAbl += 1; acc.fp += r.full.passed; acc.ft += r.full.total; acc.ap += r.ablated.passed; acc.at += r.ablated.total;
    acc.trialsAbl += r.full.trials;
    if (!(acc.lastAbl >= r.at)) acc.lastAbl = r.at;
  }
}

export function finish(acc) {
  acc.gain = acc.wt > 0 && acc.ot > 0 ? acc.wp / acc.wt - acc.op / acc.ot : null;
  acc.judgeWith = acc.wjn > 0 ? acc.wj / acc.wjn : null;
  acc.judgeWithout = acc.ojn > 0 ? acc.oj / acc.ojn : null;
  acc.inSitu = acc.ft > 0 && acc.at > 0 ? acc.fp / acc.ft - acc.ap / acc.at : null;
  return acc;
}

/* Pool runs from the window per model. Returns {models:[{model, ...acc}], all: acc}. */
export function poolRuns(runs, subject, refMs, modelOrder) {
  const by = new Map();
  const all = emptyAcc();
  for (const raw of Array.isArray(runs) ? runs : []) {
    const r = normRun(raw, subject);
    if (!r || !r.model || !inWindow(r, refMs)) continue;
    if (!by.has(r.model)) by.set(r.model, emptyAcc());
    addRun(by.get(r.model), r);
    addRun(all, r);
  }
  const order = modelOrder || [];
  const models = Array.from(by.keys()).sort((a, b) => {
    const ia = order.indexOf(a), ib = order.indexOf(b);
    if (ia !== ib) return (ia < 0 ? 1e9 : ia) - (ib < 0 ? 1e9 : ib);
    return a < b ? -1 : a > b ? 1 : 0;
  });
  return { models: models.map((m) => Object.assign({ model: m }, finish(by.get(m)))), all: finish(all) };
}

export function hasRegression(alerts, subjectKind, name) {
  return (Array.isArray(alerts) ? alerts : []).some((a) => a && a.kind === 'regression'
    && (a.subject === subjectKind) && a.name === name);
}

/* The loop's verdict (harness/gates.py, via the data file) -> the chip it
   earns. A verdict not listed here is not final, so the page's early rule
   decides between 'early' and 'insufficient'. */
export const VERDICT_CHIPS = {
  keep: 'helps', retain: 'helps', 'shorten-or-merge': 'alone', 'helps-only-alone': 'alone',
  retire: 'none', 'retire-pending': 'none', retired: 'none',
  ceiling: 'canttell', 'cannot-discriminate': 'canttell'
};

export const isDecided = (v) => typeof v === 'string' && Object.prototype.hasOwnProperty.call(VERDICT_CHIPS, v);

/* The loop's verdict for an alert's subject ('skill' or 'guidance'), or null. */
export function verdictOf(doc, subjectKind, name) {
  const list = subjectKind === 'guidance'
    ? (doc && doc.guidance && Array.isArray(doc.guidance.sections) ? doc.guidance.sections : [])
    : (doc && Array.isArray(doc.skills) ? doc.skills : []);
  const key = subjectKind === 'guidance' ? 'id' : 'name';
  const hit = list.find((x) => x && String(x[key]) === String(name));
  return hit && typeof hit.verdict === 'string' ? hit.verdict : null;
}

/* Is this alert a "Trending toward removal" row? A regression alert is,
   until the loop decides its subject; after that the decision stands and the
   alert is an ordinary one ("Score fell, decision stands"). */
export function isTrending(doc, a) {
  return !!a && a.kind === 'regression' && !isDecided(verdictOf(doc, a.subject, a.name));
}

/* The label an alert is listed under. */
export function alertKindLabel(doc, a) {
  if (a.kind === 'regression' && !isTrending(doc, a)) return STRINGS.alertRegressionDecided;
  return Object.prototype.hasOwnProperty.call(STRINGS.alertKinds, a.kind) ? STRINGS.alertKinds[a.kind] : String(a.kind);
}

/* The gain a subject's card is judged by: for a guidance section, the
   in-situ gain (all the guidance vs all of it but the section), which is the
   pair that decides it and the one every section runs; otherwise the paired
   with-vs-without gain. */
export function gainOf(acc, subject) { return subject === 'guidance' ? acc.inSitu : acc.gain; }
export function runsOf(acc, subject) { return subject === 'guidance' ? acc.nAbl : acc.n; }

export function earlyOrInsufficient(pooled, subject) {
  // Not final, but say so when every model tried so far clearly gained.
  const tried = pooled.models.filter((m) => runsOf(m, subject) > 0 && gainOf(m, subject) !== null);
  return tried.length && tried.every((m) => gainOf(m, subject) >= HELPS_MIN_GAIN - EPS) ? 'early' : 'insufficient';
}

/* The chip rule. `pooled` comes from poolRuns. With `opts.verdict` (skills
   and sections: the loop's own decision, null when it has none), the chip
   follows the loop. Without one (the whole-guidance headline, which the loop
   does not judge), the page's simple rule applies at the loop's run floor. */
export function chipFor(pooled, opts) {
  const o = opts || {};
  // A decision the loop has reached outranks a regression alert: the alert
  // compares a subject's recent scores with its own earlier ones and decides
  // nothing (harness/regression.py), so a kept subject is not trending
  // toward removal (isTrending).
  if (isDecided(o.verdict)) return VERDICT_CHIPS[o.verdict];
  if (o.regression) return 'worse';
  if (Object.prototype.hasOwnProperty.call(o, 'verdict')) return earlyOrInsufficient(pooled, o.subject);
  const eligible = pooled.models.filter((m) => m.n >= MIN_PAIRED_RUNS && m.gain !== null);
  if (!eligible.length) return earlyOrInsufficient(pooled, o.subject === 'guidance' ? 'guidance' : null);
  const helps = eligible.some((m) => m.gain >= HELPS_MIN_GAIN - EPS)
    && !eligible.some((m) => m.gain < WORSE_TOLERANCE - EPS);
  if (!helps) return 'none';
  if (o.subject === 'guidance') {
    const abl = pooled.models.filter((m) => m.nAbl >= MIN_PAIRED_RUNS && m.inSitu !== null);
    if (abl.length && abl.every((m) => m.inSitu < HELPS_MIN_GAIN - EPS)) return 'alone';
  }
  return 'helps';
}

export function sentenceFor(pooled, subject, refMs) {
  const out = [];
  for (const m of pooled.models) {
    if (m.n > 0) {
      const name = friendlyModel(m.model);
      const fn = subject === 'guidance' ? STRINGS.sentenceSection : subject === 'whole' ? STRINGS.sentenceWhole : STRINGS.sentenceSkill;
      out.push(fn(name, fmtCount(m.wp), fmtCount(m.wt), fmtCount(m.op), fmtCount(m.ot)));
    }
    if (subject === 'guidance' && m.nAbl > 0) {
      if (m.n === 0) out.push(friendlyModel(m.model) + ':');
      out.push(STRINGS.sentenceAblation(fmtCount(m.fp), fmtCount(m.ft), fmtCount(m.ap), fmtCount(m.at)));
    }
  }
  if (pooled.all.n > 0) out.push(STRINGS.tried(Math.round(pooled.all.trials), fmtDay(pooled.all.last, refMs)));
  // A section whose section-alone results are not published (they count only
  // near removal) is counted by its whole-guidance pair instead.
  else if (subject === 'guidance' && pooled.all.nAbl > 0) out.push(STRINGS.tried(Math.round(pooled.all.trialsAbl), fmtDay(pooled.all.lastAbl, refMs)));
  else out.push(STRINGS.notTried);
  return out.join(' ');
}

/* Weekly pooled gain, oldest week first. Each point: {week, start, gain}. */
export function weeklyGains(runs, subject, refMs) {
  if (!isFinite(refMs)) return [];
  const buckets = new Map();
  for (const raw of Array.isArray(runs) ? runs : []) {
    const r = normRun(raw, subject);
    // A guidance section's trend is its in-situ gain (gainOf).
    const paired = subject === 'guidance' ? (r && r.full && r.ablated) : (r && r.with && r.without);
    if (!r || !inWindow(r, refMs) || !paired) continue;
    const w = Math.max(0, Math.floor((refMs - r.at) / WEEK_MS));
    if (w >= WINDOW_WEEKS) continue;
    if (!buckets.has(w)) buckets.set(w, emptyAcc());
    addRun(buckets.get(w), r);
  }
  return Array.from(buckets.keys()).sort((a, b) => b - a).map((w) => {
    const acc = finish(buckets.get(w));
    return { week: w, start: refMs - (w + 1) * WEEK_MS, gain: gainOf(acc, subject) };
  }).filter((p) => p.gain !== null);
}

/* Sections only: the in-situ gain, in percentage points of checks passed, for
   every 100 words the section adds (words as the page shows them). */
export function gainPer100Words(pooled, bytes) {
  const g = gainOf(pooled.all, 'guidance');
  const words = wordsFor(bytes);
  return g === null ? null : (g * 100 / words) * 100;
}

/* The whole-guidance comparison, taken apart. The pooled totals mix every
   section's tasks, and the loop tests a different mix each week (sections
   leave the schedule, new tasks arrive, one task can take most of a week), so
   a pooled weekly number moves when the mix moves. These two views hold the
   mix still: one row per section, and week-to-week changes on the tasks both
   weeks share. A task is one fixture of one section. */

/* A run's compared pair as with/without: for 'guidance' the in-situ pair
   (all the guidance as with, all but the section as without). */
const pairedRun = (raw, refMs, subject) => {
  const r = normRun(raw, subject);
  if (!r || !r.model || !inWindow(r, refMs)) return null;
  if (subject === 'guidance') return r.full && r.ablated ? Object.assign({}, r, { with: r.full, without: r.ablated, full: null, ablated: null }) : null;
  return r.with && r.without ? r : null;
};
const pairedWhole = (raw, refMs) => pairedRun(raw, refMs, 'whole');
const rateOf = (p, t) => (t > 0 ? p / t : null);

/* One row per section with a paired full-vs-none run, biggest gain first.
   {id, heading, tested, n, tasks, wp, wt, op, ot, gain, last}. `tested` is
   false for a section the loop no longer evaluates (status 'skipped'). */
export function sectionSpread(sections, refMs) {
  const rows = [];
  for (const s of Array.isArray(sections) ? sections : []) {
    if (!s || !s.id) continue;
    const acc = emptyAcc();
    const tasks = new Set();
    for (const raw of Array.isArray(s.runs) ? s.runs : []) {
      const r = pairedWhole(raw, refMs);
      if (!r) continue;
      addRun(acc, r);
      tasks.add(String(r.fixture));
    }
    if (!acc.n) continue;
    finish(acc);
    rows.push({ id: String(s.id), heading: s.heading || String(s.id), tested: s.status !== 'skipped', n: acc.n, tasks: tasks.size,
      wp: acc.wp, wt: acc.wt, op: acc.op, ot: acc.ot, gain: acc.gain, last: acc.last });
  }
  return rows.sort((a, b) => (b.gain - a.gain) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/* Week buckets of the whole-guidance runs, by task. Returns
   { weeks: [{week, start, n, tasks, sections, top: {section, fixture, n}}],
     pairs: [{from, to, shared, dropped, added, then: side, now: side}] },
   both oldest first. A pair joins two consecutive weeks that had runs; its
   sides cover only the tasks tested in both: {with, without} are the mean of
   each task's pass rate (every task counted once, so a task with many runs
   weighs no more than one with few), beside the pooled check counts.
   `subject` picks the pair of arms: 'whole' (all the guidance vs none, the
   default), 'skills' (with vs without) or 'guidance' (all the guidance vs all
   but the section, shown as with and without). */
export function weekPairs(sections, refMs, subject = 'whole') {
  if (!isFinite(refMs)) return { weeks: [], pairs: [] };
  const buckets = new Map();
  for (const s of Array.isArray(sections) ? sections : []) {
    if (!s || !s.id) continue;
    for (const raw of Array.isArray(s.runs) ? s.runs : []) {
      const r = pairedRun(raw, refMs, subject);
      if (!r) continue;
      const w = Math.max(0, Math.floor((refMs - r.at) / WEEK_MS));
      if (w >= WINDOW_WEEKS) continue;
      if (!buckets.has(w)) buckets.set(w, new Map());
      const key = JSON.stringify([String(s.id), String(r.fixture)]);
      const tasks = buckets.get(w);
      if (!tasks.has(key)) tasks.set(key, Object.assign(emptyAcc(), { section: String(s.id), heading: s.heading || String(s.id), fixture: String(r.fixture) }));
      addRun(tasks.get(key), r);
    }
  }
  const order = Array.from(buckets.keys()).sort((a, b) => b - a);
  const weeks = order.map((w) => {
    const tasks = Array.from(buckets.get(w).values());
    const top = tasks.reduce((best, t) => (!best || t.n > best.n ? t : best), null);
    return { week: w, start: refMs - (w + 1) * WEEK_MS, n: tasks.reduce((sum, t) => sum + t.n, 0), tasks: tasks.length,
      sections: new Set(tasks.map((t) => t.section)).size, top: { section: top.section, heading: top.heading, fixture: top.fixture, n: top.n } };
  });
  const side = (tasks, keys) => {
    const out = { with: 0, without: 0, wp: 0, wt: 0, op: 0, ot: 0, n: 0 };
    for (const k of keys) {
      const t = tasks.get(k);
      out.with += rateOf(t.wp, t.wt); out.without += rateOf(t.op, t.ot);
      out.wp += t.wp; out.wt += t.wt; out.op += t.op; out.ot += t.ot; out.n += t.n;
    }
    out.with /= keys.length; out.without /= keys.length;
    return out;
  };
  const pairs = [];
  for (let i = 1; i < order.length; i++) {
    const a = buckets.get(order[i - 1]), b = buckets.get(order[i]);
    const keys = Array.from(a.keys()).filter((k) => b.has(k));
    pairs.push({ from: weeks[i - 1], to: weeks[i], shared: keys.length, dropped: a.size - keys.length, added: b.size - keys.length,
      then: keys.length ? side(a, keys) : null, now: keys.length ? side(b, keys) : null });
  }
  return { weeks: weeks, pairs: pairs };
}
