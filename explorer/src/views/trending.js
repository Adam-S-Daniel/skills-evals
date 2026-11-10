/* "Trending toward removal": the subjects whose recent runs score worse than
   the runs before them. It is the system working as designed, so it is a
   table of its own, one row per subject, not an alert that needs action. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel, fmt2, fmtCount, roundDecimals } from '../core/format.js';
import { h, link } from '../core/h.js';
import { skillTerm, sectionTerm, fixtureTerm, defn } from '../core/terms.js';
import { table } from './bits.js';
import { isTrending } from '../core/stats.js';

const isNum = (x) => typeof x === 'number' && isFinite(x);

/* One row per subject (kind + name), folding every model and fixture of its
   regression alerts into it. */
export function trendingRows(doc, mode) {
  const by = new Map();
  for (const a of Array.isArray(doc.alerts) ? doc.alerts : []) {
    if (!isTrending(doc, a) || (mode !== 'all' && a.subject !== (mode === 'guidance' ? 'guidance' : 'skill'))) continue;
    const key = a.subject + ':' + a.name;
    if (!by.has(key)) by.set(key, { subject: a.subject, name: String(a.name), models: [], changes: [], urls: [] });
    const row = by.get(key);
    const model = a.model ? friendlyModel(a.model) : null;
    if (model && !row.models.includes(model)) row.models.push(model);
    row.changes.push({ alert: a, model });
    if (typeof a.url === 'string' && !row.urls.includes(a.url)) row.urls.push(a.url);
  }
  return Array.from(by.values()).sort((x, y) => (x.name < y.name ? -1 : x.name > y.name ? 1 : 0));
}

const cap = (nodes) => {
  const first = nodes[0];
  return typeof first === 'string' ? [first.charAt(0).toUpperCase() + first.slice(1)].concat(nodes.slice(1)) : nodes;
};

/* An older document words the change itself ("X lost-delta on F: with minus
   without went from 0.17 to 0.0." or "X regressed: the judge mean fell by
   1.5 (threshold 1.0, noise 0.47)."): read its figures back into fields. */
export function legacyFields(a) {
  const t = String(a.text || '');
  const fixture = /^\S+ (?:lost-delta|regressed) on (\S+?):/.exec(t);
  const adv = /with minus without went from (-?[\d.]+?)\.? to (-?[\d.]+?)\.?$/.exec(t);
  if (adv) return { fixture: fixture ? fixture[1] : null, measure: 'advantage', previous: Number(adv[1]), current: Number(adv[2]) };
  const fell = /the (judge|objective) mean fell by (-?[\d.]+) \(threshold (-?[\d.]+), noise (-?[\d.]+)\)/.exec(t);
  if (fell) return { fixture: fixture ? fixture[1] : null, measure: fell[1], drop: Number(fell[2]), threshold: Number(fell[3]), noise: Number(fell[4]) };
  return {};
}

/* Whole percent, and whole percentage points, for display only. */
const pct = (x) => Math.round(x * 100) + '%';
const pointsOf = (x) => { const n = Math.round(x * 100); return n < 0 ? '\u2212' + (-n) : String(n); };

/* One window's counts, or null when the document predates them. */
function windowOf(counts, arm, when) {
  const w = counts && counts[arm] && counts[arm][when];
  return w && isNum(w.checks_passed) && isNum(w.checks_total) && w.checks_total > 0 && isNum(w.runs) ? w : null;
}
const judgeOf = (counts, when) => { const w = counts && counts.with && counts.with[when]; return w && isNum(w.judge_mean) ? w.judge_mean : null; };
const of = (w) => STRINGS.trendOf(fmtCount(w.checks_passed), fmtCount(w.checks_total));
const shareOf = (w) => STRINGS.trendShareOf(pct(w.checks_passed / w.checks_total), fmtCount(w.checks_passed), fmtCount(w.checks_total));
const earlierRuns = (w) => ['the earlier ', fmtCount(w.runs), ' ', defn('run', w.runs === 1 ? 'run' : 'runs')];
const latestRuns = (w) => ['the latest ', fmtCount(w.runs)];

/* The sentence for one measure, with "judge score", "check", "run" and
   "percentage point" as tappable terms. `up` capitalizes its first word. */
function sentence(a, noun, up) {
  const U = (t) => (up ? t.charAt(0).toUpperCase() + t.slice(1) : t);
  const counts = a.counts && typeof a.counts === 'object' ? a.counts : null;
  const wp = windowOf(counts, 'with', 'previous'), wc = windowOf(counts, 'with', 'current');
  const judge = (label) => defn('judgeScore', U(label));
  const checks = (label) => defn('check', label);
  const points = defn('percentagePoint', 'percentage points');
  const hasFromTo = isNum(a.previous) && isNum(a.current);
  if (a.measure === 'judge') {
    const nodes = [judge('judge score'), hasFromTo
      ? ' (out of 10) fell from ' + fmt2(a.previous) + ' to ' + fmt2(a.current) + ', a drop of ' + fmt2(a.drop) + '. '
      : ' (out of 10) fell by ' + fmt2(a.drop) + '. ', STRINGS.trendJudgeNeeds(fmt2(a.threshold), fmt2(a.noise))];
    if (wp && wc) nodes.push(' ', checks('Checks'), ' passed: ', of(wp), ' in ', earlierRuns(wp), ', ', of(wc), ' in ', latestRuns(wc), '.');
    return nodes;
  }
  const jp = judgeOf(counts, 'previous'), jc = judgeOf(counts, 'current');
  const judgeMoved = (what) => (isNum(jp) && isNum(jc) ? [' ', defn('judgeScore', 'Judge score'), ' (out of 10)' + what + ': ' + fmt2(jp) + ' earlier, ' + fmt2(jc) + ' lately.'] : []);
  if (a.measure === 'objective') {
    const nodes = hasFromTo && wp && wc
      ? [checks(U('checks')), ' passed fell from ', pct(a.previous), ' (' + of(wp) + ') in ', earlierRuns(wp), ' to ', pct(a.current), ' (' + of(wc) + ') in ', latestRuns(wc), '.']
      : hasFromTo ? [checks(U('checks')), ' passed fell from ' + pct(a.previous) + ' to ' + pct(a.current) + '.']
        : [checks(U('checks')), ' passed fell by ' + pointsOf(a.drop) + ' ', points, '.'];
    nodes.push(' ', STRINGS.trendChecksNeeds(pointsOf(a.threshold), pointsOf(a.noise)));
    return nodes.concat(judgeMoved(''));
  }
  const lead = [' The ' + noun + '\'s lead fell from ' + pointsOf(a.previous) + ' to ' + pointsOf(a.current) + ' ', points, '.'];
  if (!(wp && wc)) {
    return [U('the ' + noun + '\'s lead'), ' over running without it (the share of ', checks('checks'), ' passed with it minus without it) fell from ' + pointsOf(a.previous) + ' to ' + pointsOf(a.current) + ' ', points, '.'];
  }
  const op = windowOf(counts, 'without', 'previous'), oc = windowOf(counts, 'without', 'current');
  const nodes = [U('with the ' + noun + ', ') + of(wp) + ' ', checks('checks'), ' passed (' + pct(wp.checks_passed / wp.checks_total) + ') earlier and ' + of(wc) + ' (' + pct(wc.checks_passed / wc.checks_total) + ') lately'];
  if (op && oc) nodes.push('; without it, ' + of(op) + ' (' + pct(op.checks_passed / op.checks_total) + ') and ' + of(oc) + ' (' + pct(oc.checks_passed / oc.checks_total) + ')');
  nodes.push('.');
  return nodes.concat(lead, judgeMoved(' with the ' + noun));
}

/* The change as plain English, from the alert's fields when it has them. */
export function changeNodes(alert) {
  const a = alert.measure ? alert : Object.assign({}, alert, legacyFields(alert));
  const noun = STRINGS.trendKindNoun[a.subject] || 'subject';
  const fixture = typeof a.fixture === 'string' && a.fixture ? fixtureTerm(a.fixture) : null;
  let rest;
  if (a.measure === 'advantage' && isNum(a.previous) && isNum(a.current)) {
    rest = sentence(a, noun, !fixture);
  } else if ((a.measure === 'judge' || a.measure === 'objective') && isNum(a.drop) && isNum(a.threshold) && isNum(a.noise)) {
    rest = sentence(a, noun, !fixture);
  } else {
    // An older document words the change itself; its numbers are still rounded.
    return [clean(roundDecimals(a.text || ''))];
  }
  return fixture ? [STRINGS.trendOnFixture, fixture, ', '].concat(rest) : rest;
}

function subjectCell(r) {
  const label = r.subject === 'guidance' ? sectionTerm(r.name) : skillTerm(r.name);
  return h('span', null, label, h('span', { class: 'muted' }, ' · ' + STRINGS.trendingKinds[r.subject]));
}

function issueNumber(url) {
  const m = /\/issues\/(\d+)$/.exec(String(url));
  return m ? m[1] : null;
}

export function trendingView(doc, mode) {
  const rows = trendingRows(doc, mode);
  if (!rows.length) return null;
  const C = STRINGS.trendingCols;
  return h('section', { class: 'block trending' }, h('h2', null, STRINGS.trendingHeading),
    h('p', { class: 'note' }, STRINGS.trendingNote),
    table([
      { label: C.subject, sort: (r) => r.name, cell: subjectCell },
      { label: C.models, sort: (r) => r.models.join(', '), cell: (r) => r.models.join(', ') || STRINGS.noValue },
      { label: C.what, cell: (r) => h('ul', { class: 'plain' }, r.changes.map((c) => h('li', null, cap(changeNodes(c.alert)),
        r.models.length > 1 && c.model ? STRINGS.trendModelSuffix(c.model) : null))) },
      { label: C.details, cell: (r) => r.urls.map((u, i) => [i ? ', ' : null, link(u, STRINGS.trendingIssue(issueNumber(u)))]) }
    ], rows, { cls: 'trending-table' }));
}
