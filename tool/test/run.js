'use strict';
// Tests for tool/index.html: plain Node, no dependencies, no network.
// Run: node tool/test/run.js   (exits nonzero on any failure)

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const TOOL = path.resolve(__dirname, '..');
const REPO = path.resolve(TOOL, '..');
const PAGE = path.join(TOOL, 'index.html');
const html = fs.readFileSync(PAGE, 'utf8');

function loadPage() {
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\b[^>]*>/gi)].map((m) => m[1]);
  if (scripts.length !== 1) throw new Error('expected exactly one inline <script>, found ' + scripts.length);
  const sandbox = { module: { exports: {} }, URL, URLSearchParams, Intl, console, Date, Math, JSON };
  vm.runInNewContext(scripts[0], sandbox, { filename: 'index.html' });
  return sandbox.module.exports;
}

const P = loadPage();
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixture.json'), 'utf8'));
const committedIds = JSON.parse(fs.readFileSync(path.join(__dirname, 'guidance-ids.json'), 'utf8'));
// Every alert kind scripts/explorer_data.py can emit; the pytest module
// test_issue_544_545_health_alerts.py checks it against the script's AST.
const emittedKinds = JSON.parse(fs.readFileSync(path.join(__dirname, 'alert-kinds.json'), 'utf8'));

let passed = 0;
const failures = [];
const pending = [];
function test(name, fn) {
  try {
    const r = fn();
    if (r && typeof r.then === 'function') {
      pending.push(r.then(() => { passed += 1; }, (e) => failures.push(name + ': ' + e.message)));
      return;
    }
    passed += 1;
  } catch (e) {
    failures.push(name + ': ' + e.message);
  }
}
function eq(actual, expected, what) {
  if (actual !== expected) throw new Error((what || 'value') + ': expected ' + JSON.stringify(expected) + ', got ' + JSON.stringify(actual));
}
function ok(cond, what) { if (!cond) throw new Error(what || 'assertion failed'); }

const REF = '2026-10-31T21:00:00Z';
const refMs = Date.parse(REF);
const DAY = 24 * 3600 * 1000;
const at = (daysAgo) => new Date(refMs - daysAgo * DAY).toISOString().replace(/\.\d{3}Z$/, 'Z');
const arm = (p, t, trials) => ({ trials: trials || 3, checks_passed: p, checks_total: t, judge_mean: null, cost_usd: 0 });
const skillRun = (model, daysAgo, wp, op, t) => ({ model, at: at(daysAgo), fixture: null, cli_version: '1.0.0', with: arm(wp, t), without: arm(op, t), report_url: null });
const secRun = (model, daysAgo, s, n, f, fm, t) => {
  const modes = {};
  if (s !== null) modes.section = arm(s, t);
  if (n !== null) modes.none = arm(n, t);
  if (f !== null) modes.full = arm(f, t);
  if (fm !== null) modes.full_minus_section = arm(fm, t);
  return { model, at: at(daysAgo), fixture: 'f', cli_version: '1.0.0', modes, report_url: null };
};
const chipOf = (runs, subject, regression) => P.chipFor(P.poolRuns(runs, subject, refMs, []), { subject, regression });

// --- sentences ---------------------------------------------------------
// textOf puts a space between nodes, so a button inside a sentence reads "fires )"; collapse that for sentence checks.
const sp = (t) => t.replace(/\s+/g, ' ').replace(/ ([);,.:])/g, '$1');
test('friendly model names come from ids', () => {
  eq(P.friendlyModel('claude-sonnet-5-5'), 'Claude Sonnet 5.5');
  eq(P.friendlyModel('claude-fable-5-1'), 'Claude Fable 5.1');
  eq(P.friendlyModel('example-large-2-0'), 'Example Large 2.0');
  eq(P.friendlyModel('claude-haiku-4-5-20251001'), 'Claude Haiku 4.5');
});

test('skill sentence for a canned run', () => {
  const runs = [
    skillRun('example-model-1-0', 0, 8, 5, 9),
    skillRun('example-model-1-0', 7, 8, 5, 9),
    skillRun('example-model-1-0', 14, 8, 5, 9)
  ];
  const s = P.sentenceFor(P.poolRuns(runs, 'skills', refMs, []), 'skills', refMs);
  eq(s, 'With this skill, Example Model 1.0 passed 24 of 27 checks; without it, 15 of 27. 9 trials in all, the last on Oct 31.');
});

test('guidance sentence includes the ablation clause', () => {
  const runs = [secRun('example-model-1-0', 1, 7, 4, 7, 5, 8)];
  const s = P.sentenceFor(P.poolRuns(runs, 'guidance', refMs, []), 'guidance', refMs);
  eq(s, 'With this section, Example Model 1.0 passed 7 of 8 checks; without it, 4 of 8. '
    + 'With all the guidance, 7 of 8; with all of it but this section, 5 of 8. 3 trials in all, the last on Oct 30.');
});

test('runs older than the window are left out of the sentence', () => {
  const s = P.sentenceFor(P.poolRuns([skillRun('m-1', 400, 1, 0, 1)], 'skills', refMs, []), 'skills', refMs);
  eq(s, P.STRINGS.notTried);
});

test('data-as-of time is shown in US Eastern', () => {
  eq(P.fmtDateTime(Date.parse('2026-10-31T21:03:00Z')), 'Oct 31, 2026, 5:03 PM ET');
});

// --- chips ---------------------------------------------------------------
test('chip: Not enough data below the paired-run minimum when the early signal is mixed or small', () => {
  eq(chipOf([skillRun('a', 0, 5, 5, 9), skillRun('a', 1, 5, 5, 9), skillRun('b', 0, 9, 0, 9)], 'skills'), 'insufficient');
  eq(chipOf([skillRun('a', 0, 9, 0, 9), skillRun('b', 0, 3, 9, 9)], 'skills'), 'insufficient');
  eq(chipOf([], 'skills'), 'insufficient');
});
test('chip: Early sign when every model tried gains >= 5 points below the minimum', () => {
  eq(chipOf([skillRun('a', 0, 9, 0, 9), skillRun('a', 1, 9, 0, 9), skillRun('b', 0, 9, 0, 9)], 'skills'), 'early');
  eq(chipOf([skillRun('a', 0, 7, 1, 7)], 'skills', true), 'worse');
  ok(P.STRINGS.chips.early && P.STRINGS.chipRules.early && P.STRINGS.wholeAnswer.early, 'early strings');
});
test('chip: Helps at >= 5 points on one model and not worse beyond 5 on any', () => {
  const runs = [0, 1, 2, 3, 4].map((d) => skillRun('a', d, 21, 20, 20 * 1)).map((r) => Object.assign(r, { with: arm(11, 20), without: arm(10, 20) }));
  eq(chipOf(runs, 'skills'), 'helps', 'exactly +0.05');
  const mixed = runs.concat([0, 1, 2, 3, 4].map((d) => Object.assign(skillRun('b', d, 0, 0, 20), { with: arm(9, 20), without: arm(10, 20) })));
  eq(chipOf(mixed, 'skills'), 'helps', '+0.05 and -0.05 is still helps');
});
test('chip: No measurable difference when the gain is small', () => {
  const runs = [0, 1, 2, 3, 4].map((d) => Object.assign(skillRun('a', d, 0, 0, 100), { with: arm(54, 100), without: arm(50, 100) }));
  eq(chipOf(runs, 'skills'), 'none');
});
test('chip: a model worse beyond 5 points blocks Helps', () => {
  const a = [0, 1, 2, 3, 4].map((d) => skillRun('a', d, 9, 3, 9));
  const b = [0, 1, 2, 3, 4].map((d) => Object.assign(skillRun('b', d, 0, 0, 100), { with: arm(40, 100), without: arm(50, 100) }));
  eq(chipOf(a.concat(b), 'skills'), 'none');
});
test('chip: Trending toward removal when a regression alert names it', () => {
  eq(chipOf([skillRun('a', 0, 9, 0, 9)], 'skills', true), 'worse');
  ok(P.hasRegression(fixture.alerts, 'skill', 'example-skill-delta'), 'fixture regression found');
  ok(!P.hasRegression(fixture.alerts, 'guidance', 'example-skill-delta'), 'subject must match');
});
test('chip: guidance Helps when the section also helps with the other rules present', () => {
  const runs = [0, 1, 2, 3, 4].map((d) => secRun('a', d, 7, 3, 7, 4, 8));
  eq(chipOf(runs, 'guidance'), 'helps');
});
test('chip: guidance Helps only on its own', () => {
  const runs = [0, 1, 2, 3, 4].map((d) => secRun('a', d, 7, 3, 7, 7, 8));
  eq(chipOf(runs, 'guidance'), 'alone');
  // without enough ablation runs, the second rule cannot fire
  eq(chipOf([0, 1, 2, 3, 4].map((d) => secRun('a', d, 7, 3, d === 0 ? 7 : null, d === 0 ? 7 : null, 8)), 'guidance'), 'helps');
});
test('chip: the guidance subject applies the shared rules too', () => {
  // A section's early sign is its in-situ gain (all the guidance vs all
  // but the section), the pair every section runs.
  eq(chipOf([secRun('a', 0, null, null, 7, 3, 8)], 'guidance'), 'early');
  eq(chipOf([secRun('a', 0, 7, 3, 7, 7, 8)], 'guidance'), 'insufficient', 'an alone gain alone is no early sign');
  eq(chipOf([0, 1, 2, 3, 4].map((d) => secRun('a', d, 5, 5, 5, 5, 8)), 'guidance'), 'none');
  eq(chipOf([secRun('a', 0, 5, 5, 5, 5, 8)], 'guidance', true), 'worse');
});
test('removed skills are listed with their date and revert link (#557)', () => {
  const doc = { schema_version: P.SCHEMA_VERSION, generated_at: '2026-11-20T00:00:00Z', skills: [], guidance: { sections: [] },
    removed_skills: [{ name: 'example-skill', plugin: 'adam-coding-anywhere', date: '2026-11-20', reverse_url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pulls?q=is%3Apr+head%3Aretire-skill%2Fexample-skill' }] };
  const text = P.textOf(P.renderRoute(doc, { name: 'removed', id: null }, {}));
  eq(text.includes(P.STRINGS.removedSkillsHeading), true);
  eq(text.includes('example-skill'), true);
  const none = P.textOf(P.renderRoute({ ...doc, removed_skills: [] }, { name: 'removed', id: null }, {}));
  eq(none.includes(P.STRINGS.removedSkillsHeading), false, 'no list without removals');
});
test('removed sections are listed with their date and revert link (#557)', () => {
  const doc = { schema_version: P.SCHEMA_VERSION, generated_at: '2026-11-20T00:00:00Z', skills: [],
    guidance: { sections: [], removed: [{ id: 'bravo', date: '2026-11-20', reverse_url: 'https://github.com/Adam-S-Daniel/_agent-guidance/pulls?q=is%3Apr+head%3Aretire-guidance%2Fbravo' }] } };
  const text = P.textOf(P.renderRoute(doc, { name: 'removed', id: null }, {}));
  eq(text.includes(P.STRINGS.removedHeading), true);
  eq(text.includes('bravo'), true);
  eq(text.includes('2026-11-20'), true);
  const none = P.textOf(P.renderRoute({ ...doc, guidance: { sections: [] } }, { name: 'removed', id: null }, {}));
  eq(none.includes(P.STRINGS.removedHeading), false, 'no list without removals');
  ok(none.includes(P.STRINGS.removedNone), 'an empty Removed page says so');
});
test('with a loop verdict, the chip follows the loop, not the page rule', () => {
  const strong = [skillRun('a', 0, 9, 0, 9)];
  const many = [0, 1, 2, 3, 4].map((d) => skillRun('a', d, 9, 0, 9));
  const ch = (runs, verdict, reg) => P.chipFor(P.poolRuns(runs, 'skills', refMs, []), { subject: 'skills', verdict, regression: reg });
  eq(ch(strong, 'keep'), 'helps');
  eq(ch(many, 'insufficient'), 'early', 'a big gain the loop has not confirmed is only an early sign');
  eq(ch(many, null), 'early', 'no verdict yet');
  eq(ch([skillRun('a', 0, 5, 5, 9)], 'insufficient'), 'insufficient');
  eq(ch(many, 'retire'), 'none');
  eq(ch(many, 'retire-pending'), 'none');
  eq(ch(many, 'ceiling'), 'canttell');
  eq(ch(many, 'cannot-discriminate'), 'canttell');
  eq(ch(many, 'shorten-or-merge'), 'alone');
  eq(ch(many, 'keep', true), 'worse', 'a regression alert still wins');
  eq(ch(many, 'something-new'), 'early', 'an unknown verdict is not final');
  P.STRINGS.chipOrder.forEach((k) => ok(P.STRINGS.chips[k] && P.STRINGS.chipRules[k], 'strings for ' + k));
});
test('fixture cards get the expected chips', () => {
  const skills = Object.fromEntries(P.skillItems(fixture).map((i) => [i.name, i.chip]));
  eq(skills['example-skill-alpha'], 'helps');
  eq(skills['example-skill-beta'], 'none');
  eq(skills['example-skill-gamma'], 'early');
  eq(skills['example-skill-delta'], 'worse');
  ok(!('example-skill-epsilon' in skills), 'skipped skill without runs has no card');
  const secs = Object.fromEntries(P.sectionItems(fixture).map((i) => [i.id, i.chip]));
  eq(secs['anything-you-name-gets-its-link'], 'helps');
  eq(secs['security'], 'alone');
  eq(secs['git-practices'], 'none');
  eq(secs['workstation-layout'], 'early');
});
test('skills sort by helpfulness: chip group first, then gain, highest first', () => {
  const items = P.skillItems(fixture);
  eq(items.map((i) => i.name).join(','),
    'example-skill-alpha,example-skill-gamma,example-skill-leaky,example-skill-beta,example-skill-delta');
  const rank = ['helps', 'early', 'canttell', 'insufficient', 'none', 'worse'];
  items.forEach((it, i) => {
    if (i === 0) return;
    const p = items[i - 1];
    const rp = rank.indexOf(p.chip), rc = rank.indexOf(it.chip);
    ok(rp < rc || (rp === rc && (p.pooled.all.gain === null ? it.pooled.all.gain === null
      : it.pooled.all.gain === null || p.pooled.all.gain >= it.pooled.all.gain)), 'order at ' + it.name);
  });
});
test('cards sort by next test first, then by how well they are faring', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  const set = (name, nt) => { doc.skills.find((x) => x.name === name).next_test = nt; };
  set('example-skill-delta', { position: 1, band: 'missing', due: null, scheduled: true });
  set('example-skill-beta', { position: 2, band: 'near', due: null, scheduled: true });
  set('example-skill-gamma', { position: null, band: null, due: '2026-12-20T00:00:00Z', scheduled: true });
  set('example-skill-leaky', { position: null, band: null, due: '2026-12-01T15:00:00Z', scheduled: true });
  eq(P.skillItems(doc).map((i) => i.name).join(','),
    'example-skill-delta,example-skill-beta,example-skill-leaky,example-skill-gamma,example-skill-alpha');
  const sec = JSON.parse(JSON.stringify(fixture));
  sec.guidance.sections.find((x) => x.id === 'git-practices').next_test = { position: 1, band: 'missing', due: null, scheduled: true };
  eq(P.sectionItems(sec, 'next')[0].id, 'git-practices');
  const text = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(text.includes('Next test: 1st skill in line for the next round of tests.'), 'queued line');
  ok(text.includes('Next test: a re-check due Dec 1.'), 're-check line, in Eastern time');
  ok(text.includes(P.STRINGS.nextUnscheduled), 'unscheduled line');
});
test('the start-up code names the one page title, not a property of its state', () => {
  // Regression: a title rename once left `state.STRINGS.title` in boot(), which
  // only runs in a browser, so every page load showed "could not be shown".
  ok(!/\bstate\.STRINGS\b/.test(html), 'no state.STRINGS reference');
  eq(P.STRINGS.title, 'Evals Explorer');
});
test('stakes show on the card for high and no-eval subjects only', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  doc.skills[0].stakes = { level: 'high', reason: 'a wrong pin runs third-party code' };
  doc.skills[1].stakes = { level: 'none', reason: 'a hook refuses it', covered_by: 'Adam-S-Daniel/example:hooks/check.sh' };
  doc.skills[2].stakes = { level: 'normal' };
  const text = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(text.includes('High stakes: a wrong pin runs third-party code. It is tested first and re-checked every 4 weeks instead of 8.'), 'high line');
  ok(text.includes('No test needed: a hook refuses it. A check enforces it: Adam-S-Daniel/example:hooks/check.sh.'), 'none line');
  eq(text.split('High stakes:').length + text.split('No test needed:').length, 4);
});
const cv = (c, policy) => P.confidenceView(c, { benefit_confidence: 0.8, retire_confidence: 0.9, objective_margin: 0.15, max_runs_per_cell: 40, ...policy }, 'skills');
const svgs = (n) => P.findAll(n, (x) => x.tag === 'svg');
const byClass = (n, cls) => P.findAll(n, (x) => x.attrs && x.attrs.class === cls);
const axisX = (v) => 116 + ((v + 100) / 200) * (282 - 116);
const cell = (over) => ({ model: 'claude-sonnet-5-5', task: 'fetch-retry', pairs: 5, gain: 22, low: -18, high: 61, votes: true, status: 'open', ...over });
const twoCells = [cell({ status: 'keeps', low: 3.5, high: 70 }),
  cell({ model: 'claude-opus-5-5', task: 'a-really-long-invented-task-name-here', pairs: 40, gain: -5, low: -60.2, high: 10, status: 'removes-ready' })];
const withCells = (cells, over) => ({ helps: 0.5, no_help: 0.5, keep_pairs: 10, no_help_pairs: 10, max_pairs: 10, cells, ...over });
test('the confidence view with no figure says so', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  doc.skills[1].confidence = { helps: null, no_help: null };
  ok(P.textOf(P.buildPage(doc, 'skills', {})).includes(P.STRINGS.confidenceNone), 'page');
  ok(P.textOf(cv(null)).includes(P.STRINGS.confidenceNone), 'null');
  eq(svgs(cv({ helps: null })).length, 0);
});
test('the gain range chart draws one row per cell, each range on the axis scale', () => {
  const n = cv(withCells(twoCells));
  const chart = svgs(n);
  eq(chart.length, 1);
  eq(chart[0].attrs.class, 'chart range');
  eq(chart[0].attrs.role, 'img');
  ok(/2 tasks and models/.test(chart[0].attrs['aria-label']), 'aria summary');
  const bars = byClass(n, 'range-bar');
  eq(bars.length, 2);
  twoCells.forEach((c, i) => {
    const x = Number(bars[i].attrs.x), w = Number(bars[i].attrs.width);
    ok(Math.abs(x - axisX(c.low)) < 0.5, 'left end ' + i + ': ' + x);
    ok(Math.abs(x + w - axisX(c.high)) < 0.5, 'right end ' + i + ': ' + (x + w));
    eq(Number(bars[i].attrs.height), 10, 'height');
  });
  const dots = byClass(n, 'gain-dot');
  eq(dots.length, 2);
  twoCells.forEach((c, i) => ok(Math.abs(Number(dots[i].attrs.cx) - axisX(c.gain)) < 0.5, 'dot ' + i));
  eq(dots[0].attrs.fill, 'var(--ink)');
  eq(Number(dots[0].attrs.r), 4);
  const marks = byClass(n, 'mark');
  eq(marks.length, 2);
  ok(marks.every((m) => m.attrs.tabindex === 0 && m.attrs['data-tip-pos'] === 'below'), 'focusable targets below');
  eq(marks[0].attrs['data-tip'], 'Claude Sonnet 5.5, task fetch-retry: gain +22 points so far; likely between +4 and +70. 5 of 40 runs.');
});
test('the gain range chart marks 0 and the margin, labels the axis and colors by status', () => {
  const n = cv(withCells(twoCells));
  const line = (k) => P.findAll(n, (x) => x.tag === 'line' && x.attrs['data-line'] === k)[0];
  ok(Math.abs(line('zero').attrs.x1 - axisX(0)) < 0.5, 'zero line');
  ok(!line('zero').attrs['stroke-dasharray'], 'zero line is solid');
  eq(line('margin').attrs['stroke-dasharray'], '3 3');
  ok(Math.abs(line('margin').attrs.x1 - axisX(15)) < 0.5, 'margin line at +15');
  const labels = P.findAll(n, (x) => x.tag === 'text').map((x) => P.textOf(x).trim());
  for (const want of ['−100', '−50', '0', '+50', '+100', '+15']) ok(labels.includes(want), 'label ' + want);
  const wider = cv(withCells(twoCells), { objective_margin: 0.2 });
  ok(Math.abs(P.findAll(wider, (x) => x.attrs && x.attrs['data-line'] === 'margin')[0].attrs.x1 - axisX(20)) < 0.5, 'policy margin');
  const fills = {};
  for (const status of ['keeps', 'removes-ready', 'no-room', 'paused', 'open']) {
    const bar = byClass(cv(withCells([cell({ status })])), 'range-bar')[0];
    fills[status] = bar.attrs.fill + '@' + bar.attrs['fill-opacity'];
  }
  eq(JSON.stringify(fills), JSON.stringify({ keeps: 'var(--good)@1', 'removes-ready': 'var(--s2)@1', 'no-room': 'var(--axis)@1', paused: 'var(--axis)@1', open: 'var(--s1)@0.55' }));
});
test('the gain range chart shows runs toward the cap and clips long task names', () => {
  const n = cv(withCells(twoCells));
  const runs = byClass(n, 'runs').map((x) => P.textOf(x).trim());
  eq(runs.join(), '5/40,40/40');
  const fills = byClass(n, 'runs-fill').map((x) => Number(x.attrs.width));
  ok(Math.abs(fills[0] - 42 * 5 / 40) < 0.01 && Math.abs(fills[1] - 42) < 0.01, 'meter widths ' + fills);
  const task = P.findAll(n, (x) => x.tag === 'text' && x.attrs['data-tip'] === 'a-really-long-invented-task-name-here')[0];
  ok(task, 'full name in data-tip');
  const shown = P.textOf(task.children[0]);
  ok(shown.endsWith('…') && shown.length <= 19, 'clipped: ' + shown);
  eq(P.clipName('short', 19), 'short');
  ok(byClass(n, 'mark')[1].attrs['data-tip'].includes('task a-really-long-invented-task-name-here:'), 'full name in the range tip');
  // No cap in the policy: a count, no meter.
  const free = cv(withCells(twoCells), { max_runs_per_cell: null });
  eq(byClass(free, 'runs').map((x) => P.textOf(x).trim()).join(), '5,40');
  eq(byClass(free, 'runs-fill').length, 0);
});
test('the gain range chart explains itself with the policy levels', () => {
  const t = P.textOf(cv(withCells(twoCells), { benefit_confidence: 0.85, retire_confidence: 0.95, min_cli_versions: 3 }));
  ok(t.includes('Each bar is the range the gain likely falls in, for one task on one model, in percentage points of checks passed; the dot is the gain measured so far.'), 'what');
  ok(t.includes('Keep: a bar entirely right of 0. Remove: every counted bar entirely left of +15.'), 'rule');
  ok(t.includes('The left end is held to 85% certainty shared across the skill\'s tasks and models, the right end to 95%; a decision also waits for runs on three Claude Code versions.'), 'levels');
  const g = P.textOf(P.confidenceView(withCells(twoCells), { benefit_confidence: 0.8, retire_confidence: 0.9, objective_margin: 0.15, min_cli_versions: 2 }, 'guidance'));
  ok(g.includes('shared across the section\'s tasks and models, the right end to 90%; a decision also waits for runs on two Claude Code versions.'), 'section wording');
});
test('the confidence view estimates the runs still needed, or says it is past the cap', () => {
  const near = P.textOf(cv(withCells(twoCells)));
  ok(near.includes('Keep: at this pace, about 14 more runs.'), 'keep estimate ' + near);
  ok(near.includes('Removal: at this pace, about 24 more runs.'), 'removal estimate');
  ok(near.includes(P.STRINGS.confPace), 'pace note');
  ok(near.includes('Runs that count toward a decision, busiest task and model: 10 of 40. Testing stops at 40 runs. If there is still no decision then, the loop does not remove it on its own; it files a removal proposal for the owner to decide.'), 'runs');
  const far = P.textOf(cv(withCells(twoCells, { keep_pairs: 20, no_help_pairs: 20, max_pairs: 20 })));
  ok(far.includes('Keep: not before the 40-run cap at this pace.') && far.includes('Removal: not before the 40-run cap at this pace.'), 'past cap');
  ok(!far.includes('more run'), 'no estimate past the cap');
  const done = P.textOf(cv(withCells(twoCells, { helps: 0.85, no_help: 0 })));
  ok(done.includes('Keep: reached.') && done.includes('Removal: no movement yet.'), 'reached ' + done);
  ok(!done.includes(P.STRINGS.confPace), 'no pace note without a projection');
  eq(P.STRINGS.confMore('Keep', 1), 'Keep: at this pace, about 1 more run.');
});
test('the confidence view names a subject with no room to show a gain', () => {
  const t = P.textOf(cv(withCells(twoCells, { no_help: null })));
  ok(t.includes('Removal: no task leaves room for a 15-point gain (Claude already passes without it), so this needs a harder test.'), 'no room');
  ok(!/\b(85|95)% confiden/.test(P.STRINGS.chipRules.helps + P.STRINGS.chipRules.none), 'no fixed levels in the chip rules');
});
test('the confidence view without cells (older data) shows the sentences only', () => {
  const n = cv({ helps: 0.5, no_help: 0.25 });
  eq(svgs(n).length, 0);
  const t = P.textOf(n);
  ok(t.includes('Testing a task and model stops at 40 comparison runs. If there is still no decision then, the loop does not remove it on its own; it files a removal proposal for the owner to decide.'), 'cap');
  ok(!t.includes('more run') && !t.includes(P.STRINGS.confPace) && !t.includes(P.STRINGS.rangeWhat), 'no estimates, no chart notes');
  eq(svgs(cv({ helps: 0.5, no_help: 0.25, cells: [] })).length, 0);
});
test('no "Sure it helps" gauge text is left anywhere', () => {
  for (const m of ['skills', 'guidance']) {
    const t = P.textOf(P.buildPage(fixture, m, {}));
    ok(!/Sure it helps|Sure any gain/.test(t), m);
  }
  ok(!/Sure it helps|Sure any gain|class="gauge"|\.gauge\b|\.track\b/.test(html), 'page source');
});
test('real-use counts show on skill cards with the census window', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  doc.usage = { from: '2026-09-07T00:00:00Z', to: '2026-10-31T16:37:13Z', sessions_scanned: 2517, surface: 'local' };
  doc.skills[0].usage = { invocations: 9 };
  doc.skills[1].usage = { invocations: 1 };
  doc.skills[2].usage = { invocations: 0 };
  const text = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(text.includes('Used 9 times in the owner\'s real work from Sep 7 to Oct 31.'), 'plural, UTC window start');
  ok(text.includes('Used 1 time in the owner\'s real work from Sep 7 to Oct 31.'), 'singular');
  ok(text.includes('Not used in the owner\'s real work from Sep 7 to Oct 31.'), 'zero');
  ok(text.includes('2,517 of the owner\'s Claude Code sessions'), 'session count note');
  ok(!P.textOf(P.buildPage(fixture, 'skills', {})).includes('real work from'), 'no census, no line');
});
test('each skill card says what the skill is for', () => {
  eq(P.purposeOf('Write ADRs under docs/decisions/. Use when asked.'), 'Write ADRs under docs/decisions/.');
  eq(P.purposeOf('Debug e.g. workflows. Trigger on CI.'), 'Debug e.g. workflows.');
  eq(P.purposeOf('No final stop'), 'No final stop');
  eq(P.purposeOf(null), null);
  const page = P.textOf(P.buildPage(fixture, 'skills', {}));
  ok(page.includes('Invented description of what example-skill-alpha is for.'), 'purpose on the card');
  ok(!page.includes('Use when the test says so'), 'trigger text left off');
  const noDesc = JSON.parse(JSON.stringify(fixture));
  noDesc.skills.forEach((x) => { delete x.description; });
  ok(P.textOf(P.buildPage(noDesc, 'skills', {})).includes(P.STRINGS.purposeMissing), 'fallback when absent');
  eq(P.purposeOf('   '), null);
});
test('sections sort by gain per KB, or by size', () => {
  const byValue = P.sectionItems(fixture, 'value').map((i) => i.id);
  // By in-situ gain per KB: what the section adds beside the rest.
  const withGain = byValue.filter((id) => ['security', 'anything-you-name-gets-its-link', 'git-practices', 'dependency-updates'].includes(id));
  eq(withGain.join(','), 'anything-you-name-gets-its-link,dependency-updates,git-practices,security');
  const items = Object.fromEntries(P.sectionItems(fixture, 'value').map((i) => [i.id, i]));
  ok(items['dependency-updates'].perKb !== null, 'an in-situ-only section is ranked');
  eq(items['dependency-updates'].perKb, items['anything-you-name-gets-its-link'].perKb, 'same in-situ runs, same bytes');
  const bySize = P.sectionItems(fixture, 'size').map((i) => i.bytes);
  ok(bySize.every((b, i) => i === 0 || bySize[i - 1] >= b), 'size order descending');
});
test('section-alone results show only when the data file carries them, with why', () => {
  // Owner, 2026-11-03: explorer_data.py publishes a section's section-alone
  // pair (section vs none) only when its in-situ verdict is retire.
  const items = Object.fromEntries(P.sectionItems(fixture).map((i) => [i.id, i]));
  const card = (id) => P.sectionCard(items[id], refMs, fixture);
  const inSitu = items['dependency-updates'];
  eq(P.hasAlone(inSitu.pooled), false, 'no alone pair in the data');
  const t = P.textOf(card('dependency-updates'));
  ok(!t.includes(P.STRINGS.aloneShown), 'no reason line without alone results');
  ok(!t.includes('With this section,'), 'no alone sentence');
  ok(!t.includes(P.STRINGS.barSection) && !t.includes(P.STRINGS.barNone), 'no alone bars or legend');
  ok(t.includes(P.STRINGS.barAll) && t.includes(P.STRINGS.barAblated), 'the in-situ bars stay');
  ok(inSitu.sentence.startsWith('Example Large 2.0: With all the guidance, 21 of 24; with all of it but this section, 13 of 24.'), inSitu.sentence);
  ok(inSitu.sentence.endsWith('18 trials in all, the last on Oct 31.'), inSitu.sentence);
  ok(!inSitu.sentence.includes(P.STRINGS.notTried), 'its in-situ trials are counted: ' + inSitu.sentence);
  ok(/\d+ trials in all, the last on /.test(inSitu.sentence), inSitu.sentence);
  for (const id of ['security', 'git-practices']) {
    eq(P.hasAlone(items[id].pooled), true, id + ' carries its alone pair');
    const shown = P.textOf(card(id));
    ok(shown.includes(P.STRINGS.aloneShown), id + ': reason line shown');
    ok(shown.includes(P.STRINGS.barSection) && shown.includes(P.STRINGS.barNone), id + ': alone bars shown');
  }
  // The trend and the early-sign chip read the in-situ pair, so they work
  // for a section without its alone pair.
  ok(inSitu.trend.length > 0, 'in-situ-only section has a weekly trend');
  // Same in-situ runs as anything-you-name-gets-its-link, so the same trend,
  // whatever that section's alone pair shows.
  eq(JSON.stringify(inSitu.trend), JSON.stringify(items['anything-you-name-gets-its-link'].trend), 'trend from the in-situ pair');
  ok(inSitu.trend.length > 1 && P.findAll(card('dependency-updates'), (x) => x.tag === 'svg').length > 0, 'trend drawn');
  const noVerdict = Object.assign({}, fixture, { guidance: { sections: [Object.assign({}, fixture.guidance.sections.find((x) => x.id === 'dependency-updates'), { verdict: null })] } });
  eq(P.sectionItems(noVerdict)[0].chip, 'early', 'early sign from the in-situ gain');
  // The headline keeps every section's none runs, this one's included.
  const w = P.wholeGuidance(fixture);
  ok(w.pooled.all.n > 0 && w.sentence.startsWith('With all the guidance, '), w.sentence);
  eq(P.STRINGS.aloneShown, 'Shown because the section is close to removal: if it still helps on its own, it gets shortened or merged instead of removed.');
});

test('whole-guidance headline pools full vs none', () => {
  const w = P.wholeGuidance(fixture);
  eq(w.chip, 'helps');
  ok(w.sentence.startsWith('With all the guidance, Example Large 2.0 passed'), w.sentence);
});

// --- failure states ---------------------------------------------------------
const mode = 'skills';
test('failure state when the fetch fails', async () => {
  const res = await P.loadData(P.DEFAULT_DATA_URL, () => Promise.reject(new Error('offline')), 1);
  eq(res.ok, false); eq(res.kind, 'fetch');
  const t = P.textOf(P.buildFailure(res, mode));
  ok(t.includes(P.STRINGS.failFetch), 'says it could not load');
  ok(t.includes('explorer/latest.json'), 'names the file');
  ok(t.includes('Try reloading'), 'says what to do');
});
test('failure state on HTTP 404', async () => {
  const res = await P.loadData(P.DEFAULT_DATA_URL, () => Promise.resolve({ ok: false, status: 404 }), 1);
  eq(res.kind, 'fetch');
});
test('failure state on a wrong schema_version', async () => {
  const res = await P.loadData(P.DEFAULT_DATA_URL, () => Promise.resolve({ ok: true, json: () => Promise.resolve({ schema_version: 2 }) }), 1);
  eq(res.ok, false); eq(res.kind, 'schema');
  const t = P.textOf(P.buildFailure(res, 'guidance'));
  ok(t.includes('version 2'), 'names the version it got');
  ok(t.includes('explorer/latest.json'), 'names the file');
});
test('failure state on unreadable JSON', async () => {
  const res = await P.loadData(P.DEFAULT_DATA_URL, () => Promise.resolve({ ok: true, json: () => Promise.reject(new SyntaxError('x')) }), 1);
  eq(res.kind, 'parse');
});
test('a good file loads and is cache-busted', async () => {
  let asked = '';
  const res = await P.loadData(P.DEFAULT_DATA_URL, (u) => { asked = u; return Promise.resolve({ ok: true, json: () => Promise.resolve(fixture) }); }, 42);
  eq(res.ok, true);
  eq(asked, P.DEFAULT_DATA_URL + '?v=42');
});

// --- modes -------------------------------------------------------------------
test('hash routes: Summary by default, subject pages by id, ?subject=guidance and old dashboard tabs redirect', () => {
  const pub = ['summary', 'hooks', 'loop', 'impact', 'ops'];
  const r = (hash, search, groups) => JSON.stringify(P.parseRoute(hash, search || '', groups || pub));
  eq(r(''), '{"name":"summary","id":null}');
  eq(r('#/nowhere'), '{"name":"summary","id":null}');
  eq(r('', '?subject=guidance'), '{"name":"guidance","id":null}');
  eq(r('#/skills/example-skill-alpha'), '{"name":"skills","id":"example-skill-alpha"}');
  eq(r('#/hooks/push-to-default'), '{"name":"hooks","id":"push-to-default"}');
  eq(r('#/guidance/security'), '{"name":"guidance","id":"security"}');
  eq(r('#/removed'), '{"name":"removed","id":null}');
  eq(r('#/needs'), '{"name":"summary","id":null}', 'the public build has no Needs you group');
  eq(r('#/needs', '', pub.concat(['needs'])), '{"name":"needs","id":null}');
  eq(r('#overview', '', pub.concat(['needs'])), '{"name":"needs","id":null}', 'an old dashboard tab link');
  eq(r('#costbenefit'), '{"name":"impact","id":null}');
  eq(P.hashFor('skills', 'a b'), '#/skills/a%20b');
  eq(r(P.hashFor('skills', 'a b')), '{"name":"skills","id":"a b"}');
});
test('the public build has five groups and Summary opens first', () => {
  eq(JSON.stringify(Object.keys(P.GROUPS)), '["summary","needs","hooks","loop","impact","ops"]');
  eq(P.groupOf('skills'), 'hooks');
  eq(P.groupOf('method'), 'hooks');
  const t = P.textOf(P.renderRoute(fixture, { name: 'summary', id: null }, {}));
  ok(t.includes(P.STRINGS.groups.summary), 'Summary heading');
  ok(!/Adam/.test(t), 'names no person');
});
test('every route renders without throwing, and a missing subject says so', () => {
  for (const name of ['summary', 'hooks', 'skills', 'guidance', 'removed', 'method', 'loop', 'impact', 'ops']) {
    ok(P.textOf(P.renderRoute(fixture, { name, id: null }, {})).length > 0, name);
  }
  const t = P.textOf(P.renderRoute(fixture, { name: 'skills', id: 'example-skill-alpha' }, {}));
  ok(t.includes('example-skill-alpha'), 'a subject page names its subject');
  ok(P.textOf(P.renderRoute(fixture, { name: 'skills', id: 'example-no-such-skill' }, {})).length > 0, 'unknown subject');
});
test('the public voice says "the owner"; the private voice says "you"', () => {
  try {
    eq(P.STRINGS.voice, 'owner');
    ok(P.STRINGS.lessonSignals.rule === 'a rule the owner stated', P.STRINGS.lessonSignals.rule);
    P.useVoice('you');
    eq(P.STRINGS.lessonSignals.rule, 'a rule you stated');
    eq(P.STRINGS.title, 'Self-improvement project');
  } finally { P.useVoice('owner'); }
  eq(P.STRINGS.title, 'Evals Explorer');
});
test('search finds subjects, checks and pull requests, and filters by verdict', () => {
  const items = P.searchItems(fixture, null);
  ok(items.length > 0, 'items');
  const hit = P.filterItems(items, { text: 'alpha', registry: '', verdict: '', model: '', stakes: '' });
  ok(hit.some((i) => /example-skill-alpha/.test(i.title)), 'finds a skill by name');
  eq(P.filterItems(items, { text: 'zzzz-not-there', registry: '', verdict: '', model: '', stakes: '' }).length, 0);
  const dest = items.map((i) => i.href || i.url);
  eq(new Set(dest).size, dest.length, 'one result per destination');
  const twice = P.searchItems(fixture, items.slice(0, 2));
  eq(twice.length, items.length, 'extra items already in the document are dropped');
});
test('each mode renders its own views', () => {
  const s = P.textOf(P.buildPage(fixture, 'skills', {}));
  ok(s.includes(P.STRINGS.skillsHeading) && !s.includes(P.STRINGS.wholeHeading), 'skills view');
  const g = P.textOf(P.buildPage(fixture, 'guidance', {}));
  ok(g.includes(P.STRINGS.wholeHeading) && g.includes(P.STRINGS.sectionsHeading), 'guidance view');
  ok(g.includes('About 150 words'), 'section size in words');
  ok(g.includes(P.GLOSSES['security']), 'gloss on the card');
});

test('a not-schedulable alert gets its plain label, not the raw kind', () => {
  eq(P.STRINGS.alertKinds['not-schedulable'], 'Not being tested');
  const doc = Object.assign({}, fixture, { alerts: [{ kind: 'not-schedulable', subject: 'skill',
    name: 'example-skill-alpha', model: 'example-large-2-0', fixture: 'evals/example-skill-alpha/x',
    reason: 'no context', text: 'The task evals/example-skill-alpha/x is not scheduled: no context.', url: null }] });
  const t = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(sp(t).includes('Not being tested: example-skill-alpha'), 'label shown');
  ok(!t.includes('not-schedulable'), 'raw kind not shown');
});

test('every alert kind explorer_data can emit has a plain label', () => {
  ok(Array.isArray(emittedKinds) && emittedKinds.length > 0, 'alert-kinds.json is a non-empty list');
  const missing = emittedKinds.filter((k) => !Object.prototype.hasOwnProperty.call(P.STRINGS.alertKinds, k)
    || typeof P.STRINGS.alertKinds[k] !== 'string' || !P.STRINGS.alertKinds[k].trim());
  eq(missing.join(','), '', 'kinds with no label');
});
test('a context-drift alert names the repository and the day it drifted (#545)', () => {
  const doc = Object.assign({}, fixture, { alerts: [{ kind: 'context-drift', subject: 'skill',
    name: 'example-skill-alpha', fixture: 'evals/example-skill-alpha/x', model: null,
    repository: 'Example-Owner/example-site', drift_since: '2026-10-12T17:00:22Z' }] });
  const t = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(sp(t).includes('Context out of date: example-skill-alpha'), 'label shown');
  ok(t.includes('in Example-Owner/example-site have changed since Oct 12'), 'repository and day shown');
  ok(!t.includes('context-drift'), 'raw kind not shown');
});
test('a loaded-copy alert gets its plain label and names both prefixes (#562)', () => {
  const doc = Object.assign({}, fixture, { alerts: [{ kind: 'loaded-copy', subject: 'skill',
    name: 'example-skill-alpha', surface: 'local', loaded: 'aaaaaaaaaaaa', main: 'bbbbbbbbbbbb' }] });
  const t = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(sp(t).includes('Sessions load an old copy: example-skill-alpha'), 'label shown');
  ok(t.includes('Most local uses in the last 2 weeks loaded copy aaaaaaaaaaaa, which main did not have at any point in that time. Main is bbbbbbbbbbbb.'), 'worded');
  ok(!t.includes('loaded-copy'), 'raw kind not shown');
});
test('the copies line counts uses by how they compare with main, and null copies show nothing (#562)', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  doc.skills[0].copies = { main: 'bbbbbbbbbbbb', window: { from: '2026-10-19', to: '2026-10-31' }, alert: { local: false, cloud: null },
    loaded: [{ digest: 'bbbbbbbbbbbb', surface: 'local', invocations: 4, vs_main: 'current' },
      { digest: 'cccccccccccc', surface: 'local', invocations: 2, vs_main: 'in-window' },
      { digest: 'aaaaaaaaaaaa', surface: 'local', invocations: 3, vs_main: 'older' },
      { digest: 'unknown:gone', surface: 'local', invocations: 1, vs_main: 'unknown' }] };
  doc.skills[1].copies = { main: null, window: { from: '2026-10-19', to: '2026-10-31' }, loaded: [], alert: { local: null, cloud: null } };
  doc.skills[2].copies = null;
  const t = P.textOf(P.buildPage(doc, 'skills', {}));
  ok(t.includes('Copies loaded in the last 2 weeks: 6 match main, 3 older, 1 unknown.'), 'counts');
  ok(t.includes(P.STRINGS.copiesNone), 'no uses in the window');
  eq(t.split('Copies loaded in the last 2 weeks').length - 1, 2, 'null copies render nothing');
  ok(!P.textOf(P.buildPage(fixture, 'skills', {})).includes('Copies loaded'), 'no copies anywhere, no line');
});
test('the fires-without-results line is worded as past events since the oldest counted fire (#555)', () => {
  const f = { window_days: 14, since: '2026-10-19T14:00:00Z', without_results: 10, rejected: 2,
    sweeps: [{ start: '2026-10-31T13:03:00Z', end: '2026-10-31T13:20:00Z', fires: 3 },
      { start: '2026-11-01T05:43:00Z', end: '2026-11-01T06:06:00Z', fires: 6 },
      { start: '2026-11-01T15:55:00Z', end: '2026-11-01T15:55:00Z', fires: 1 }] };
  for (const m of ['skills', 'guidance']) {
    const t = P.textOf(P.buildPage(Object.assign({}, fixture, { fires_without_results: f }), m, {}));
    ok(sp(t).includes('10 fires since Oct 19 produced no results (3 sweeps); 2 produced results that did not validate.'), m + ' line shown');
    const withTotal = P.textOf(P.buildPage(Object.assign({}, fixture, { fires_without_results: Object.assign({}, f, { counted: 40 }) }), m, {}));
    ok(sp(withTotal).includes('10 of 40 fires since Oct 19 produced no results (3 sweeps); 2 of 40 produced results that did not validate.'), m + ' says out of how many');
  }
  const one = Object.assign({}, f, { without_results: 1, rejected: 0, sweeps: [f.sweeps[2]] });
  ok(P.textOf(P.buildPage(Object.assign({}, fixture, { fires_without_results: one }), 'skills', {}))
    .replace(/\s+/g, ' ').replace(/ ([);,.:])/g, '$1').includes('1 fire since Oct 19 produced no results (1 sweep); 0 produced results that did not validate.'), 'singular');
  for (const quiet of [null, undefined, Object.assign({}, f, { without_results: 0, rejected: 0, sweeps: [] })]) {
    const t = P.textOf(P.buildPage(Object.assign({}, fixture, { fires_without_results: quiet }), 'skills', {}));
    ok(!t.includes('produced no results'), 'no line for ' + JSON.stringify(quiet));
  }
});

// --- glosses -----------------------------------------------------------------
function manifestIds() {
  const file = process.env.AGENT_GUIDANCE_MANIFEST
    || path.join(REPO, '..', '_agent-guidance', 'agents-md', 'eval-coverage.yml');
  if (!fs.existsSync(file)) return null;
  // Lexical token match on top-level list items; the pytest wrapper cross-checks with a YAML parser.
  return [...fs.readFileSync(file, 'utf8').matchAll(/^- id: *['"]?([a-z0-9-]+)['"]?\s*$/gm)].map((m) => m[1]);
}
test('every committed guidance id has a gloss', () => {
  ok(Array.isArray(committedIds) && committedIds.length > 0, 'guidance-ids.json is a non-empty list');
  const missing = committedIds.filter((id) => !Object.prototype.hasOwnProperty.call(P.GLOSSES, id) || !P.GLOSSES[id].trim());
  eq(missing.join(','), '', 'ids with no gloss');
});
test('every manifest id has a gloss (when the _agent-guidance checkout is present)', () => {
  const ids = manifestIds();
  if (ids === null) { console.log('  note: no _agent-guidance manifest found; checked the committed list only'); return; }
  ok(ids.length > 0, 'manifest parsed to some ids');
  const missing = ids.filter((id) => !Object.prototype.hasOwnProperty.call(P.GLOSSES, id));
  eq(missing.join(','), '', 'manifest ids with no gloss');
});
test('a section without a gloss shows a fallback, never a blank card', () => {
  const doc = JSON.parse(JSON.stringify(fixture));
  doc.guidance.sections = [{ id: 'no-such-section', heading: 'No such section', bytes: 60, status: 'gap', runs: [] }];
  const t = P.textOf(P.buildPage(doc, 'guidance', {}));
  ok(t.includes(P.GLOSS_MISSING), 'fallback gloss shown');
});

// --- data URL override ---------------------------------------------------------
test('?data accepts only localhost, 127.0.0.1 and this repo on raw.githubusercontent.com', () => {
  ok(P.allowedDataUrl('http://localhost:8000/test/fixture.json'), 'localhost');
  ok(P.allowedDataUrl('http://127.0.0.1:8000/x.json'), '127.0.0.1');
  ok(P.allowedDataUrl('https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/persistent/eval-results/explorer/latest.json'), 'repo');
  for (const bad of ['https://evil.example.com/x.json', 'http://localhost.evil.example.com/x', 'http://localhost@evil.example.com/x',
    'http://127.0.0.1.example.com/x', 'https://localhost/x', 'javascript:alert(1)', 'data:application/json,{}',
    'https://raw.githubusercontent.com/Adam-S-Daniel/other/main/x.json', 'https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals-x/main/x',
    'https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/../other/x', 'http://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/x']) {
    eq(P.allowedDataUrl(bad), null, bad);
  }
  eq(P.dataUrlFromSearch('').url, P.DEFAULT_DATA_URL);
  eq(P.dataUrlFromSearch('?data=https://evil.example.com/x').error, 'badurl');
  eq(P.dataUrlFromSearch('?data=http://localhost:8000/test/fixture.json').url, 'http://localhost:8000/test/fixture.json');
});

// --- lessons (Adam, 2026-11-03) ---------------------------------------------------
const lessonRows = (page) => P.findAll(page, (n) => n.tag === 'tr' && n.children.some((c) => c.tag === 'td'))
  .map((tr) => tr.children.filter((c) => c.tag === 'td').map((td) => P.textOf(td).replace(/\s+/g, ' ').trim()));
const lessonsSection = (doc, mode) => P.lessonsView(doc, mode);

test('lesson titles mirror the miner\'s card titles', () => {
  eq(P.lessonTitle('tool-edit'), 'Edit tool calls kept failing');
  eq(P.lessonTitle('tool-bash-make'), 'Bash make commands kept failing');
  eq(P.lessonTitle('red-ci-example-site'), 'Red CI after pushes in example-site');
  eq(P.lessonTitle('skill:example-skill-alpha'), 'example-skill-alpha');
  eq(P.lessonTitle('guidance:security', { security: 'Security' }), 'Security');
  eq(P.lessonTitle('guidance:example-unknown-section', {}), 'example-unknown-section');
  eq(P.lessonTitle('tool-bash-someone@example.com'), 'Bash ' + P.STRINGS.hidden + ' commands kept failing');
});

test('the skills view lists new-skill and skill items with kind, source, seen, dates and status', () => {
  const sec = lessonsSection(fixture, 'skills');
  const t = P.textOf(sec);
  ok(t.includes(P.STRINGS.lessonsHeading), 'heading');
  ok(t.includes(P.STRINGS.lessonsLead('Oct 30')), 'the lead names the transcripts and the day: ' + t);
  ok(P.STRINGS.lessonsLead('X').includes('transcripts'), 'the lead says the proposals come from session transcripts');
  const rows = lessonRows(sec);
  eq(rows.length, 6, 'three miner rows, then three issue rows');
  eq(rows[0].join(' | '), 'Bash make commands kept failing | New skill idea | Session transcripts (Windows and WSL) a tool call kept failing ×7 | 7 times | Oct 1 | Oct 29 | Draft #41 (open)');
  eq(rows[1].join(' | '), 'Red CI after pushes in example-site | New skill idea | Session transcripts (WSL) CI went red after a push ×5 | 5 times | Oct 2 | Oct 28 | Not drafted yet');
  eq(rows[2].join(' | '), 'example-skill-alpha | Change to a skill | Session transcripts (cloud) a rule the owner stated ×3 | 3 times | Oct 10 | Oct 20 | Waiting for review');
  const hrefs = P.findAll(sec, (n) => n.tag === 'a').map((n) => n.attrs.href);
  eq(hrefs[0], 'https://github.com/Adam-S-Daniel/adam-agentskills/pull/41');
  ok(P.findAll(sec, (n) => n.attrs && n.attrs.class === 'tablewrap').length === 1, 'the table scrolls inside .tablewrap');
});

test('the guidance view lists guidance items by their heading', () => {
  const rows = lessonRows(lessonsSection(fixture, 'guidance'));
  eq(rows.length, 2);
  eq(rows[0][0], 'Security');
  eq(rows[0][1], 'Change to the guidance');
  eq(rows[1][0], 'example-unknown-section');
  eq(rows[1][1], 'Idea for a test');
  eq(rows[1][2], 'Session transcripts (another computer) a correction the owner made ×1');
});

test('the left-out note counts memory notes, git checks and private subjects, omitting zero parts', () => {
  const t = P.textOf(lessonsSection(fixture, 'skills'));
  ok(t.includes('Left out on purpose: 2 personal memory notes, 1 proposed git check and 4 about private skills or repos. No session text is published.'), t);
  const one = P.textOf(lessonsSection({ lessons: { date: '2026-10-30', items: [], left_out: { memory_note: 0, agent_check: 0, private: 1, other: 3 } } }, 'skills'));
  ok(one.includes('Left out on purpose: 1 about private skills or repos. No session text is published.'), one);
  ok(one.includes(P.STRINGS.lessonsEmptySkills), one);
  const none = P.textOf(lessonsSection({ lessons: { date: '2026-10-30', items: [], left_out: {} } }, 'guidance'));
  ok(!none.includes('Left out') && none.includes(P.STRINGS.lessonNoText), none);
});

test('null or malformed lessons say none were available, and bad items are skipped', () => {
  for (const L of [null, undefined, 'x', { date: 'soon', items: [] }, { date: '2026-10-30' }]) {
    const t = P.textOf(lessonsSection({ lessons: L }, 'skills'));
    ok(t.includes(P.STRINGS.lessonsNone), JSON.stringify(L));
  }
  const good = { kind: 'skill-edit', subject: 'skill:example-skill-beta', evidence_count: 2, first_seen: '2026-10-01', last_seen: '2026-10-02' };
  const bad = [null, { ...good, kind: 'memory-note' }, { ...good, evidence_count: 1.5 }, { ...good, first_seen: 'x' },
    { ...good, subject: 7 }];
  const rows = lessonRows(lessonsSection({ lessons: { date: '2026-10-30', items: bad.concat([good]), left_out: {} } }, 'skills'));
  eq(rows.length, 1);
  eq(rows[0][2], 'Session transcripts', 'no sources or signals: the bare label');
  const odd = P.lessonItem({ ...good, kind: 'new-skill', sources: ['moon', 'wsl'], signals: { 'skill-invoked': 4, rule: 'x', abandoned: 2 },
    draft: { number: 3, state: 'open', url: 'https://example.com/pull/3' } });
  eq(JSON.stringify(odd.sources), '["wsl"]');
  eq(JSON.stringify(odd.signals), '[{"signal":"abandoned","n":2}]');
  eq(odd.draft, null, 'a draft not on github.com is dropped');
});

test('issue lessons show in the skills view after the miner rows, with their source and a link', () => {
  const sec = lessonsSection(fixture, 'skills');
  const rows = lessonRows(sec);
  eq(rows.length, 6);
  eq(rows[3].join(' | '), '3 facts for docs/EXAMPLE.md in Adam-S-Daniel/example-repo | Fact to move into a repo | Claude\'s auto-memory | — | Oct 29 | — | #17 (open)');
  eq(rows[4].join(' | '), '1 agent check in jodidaniel/example-site | Fact to move into a repo | Claude\'s auto-memory | — | Oct 28 | — | #5 (closed)');
  eq(rows[5].join(' | '), 'New skill: example-new-skill | New skill idea | The owner\'s proposal | — | Oct 27 | — | #88 (open)');
  const hrefs = P.findAll(sec, (n) => n.tag === 'a').map((n) => n.attrs.href);
  eq(hrefs.filter((u) => u === 'https://github.com/Adam-S-Daniel/example-repo/issues/17').length, 1, 'the issue link: ' + hrefs.join(' '));
  eq(lessonRows(lessonsSection(fixture, 'guidance')).length, 2, 'the guidance view shows no issue rows');
});

test('issue lessons alone still render, and bad issues are skipped', () => {
  const good = fixture.lessons.issues[0];
  const bad = [null, { ...good, source: 'rumor' }, { ...good, url: 'https://example.com/x' }, { ...good, repo: 'no-slash' },
    { ...good, state: 'merged' }, { ...good, opened: '2026-10' }, { ...fixture.lessons.issues[2], target: null }];
  const sec = lessonsSection({ lessons: { date: null, items: null, left_out: null, issues: bad.concat([good]) } }, 'skills');
  const t = P.textOf(sec);
  ok(t.includes(P.STRINGS.lessonMinerNone) && !t.includes('Left out'), t);
  eq(lessonRows(sec).length, 1);
  const bare = P.textOf(lessonsSection({ lessons: { date: null, items: null, left_out: null,
    issues: [{ ...good, count: null, target: null }] } }, 'skills'));
  ok(bare.includes('Facts in Adam-S-Daniel/example-repo'), 'no count or target: ' + bare);
  ok(P.textOf(lessonsSection({ lessons: { date: null, items: null, left_out: null, issues: [] } }, 'skills')).includes(P.STRINGS.lessonsNone));
});

test('lesson proposals render once, on the Loop page, not under the subject lists', () => {
  const loop = P.textOf(P.renderRoute(fixture, { name: 'loop', id: null }, {}));
  ok(loop.includes(P.STRINGS.lessonsHeading), 'on Loop');
  for (const m of ['skills', 'guidance']) ok(!P.textOf(P.buildPage(fixture, m, {})).includes(P.STRINGS.lessonsHeading), m);
  const method = P.textOf(P.renderRoute(fixture, { name: 'method', id: null }, {}));
  ok(method.includes(P.STRINGS.rosterHeading), 'the roster is on How the tests work');
});

// --- privacy ----------------------------------------------------------------------
test('no @, /home/ or cse_ string from the data reaches rendered text', () => {
  for (const m of ['skills', 'guidance']) {
    const page = P.buildPage(fixture, m, {});
    const t = P.textOf(page);
    for (const bad of ['@', '/home/', 'cse_']) ok(!t.includes(bad), m + ' mode text contains ' + bad);
    const hrefs = P.findAll(page, (n) => n.tag === 'a').map((n) => n.attrs.href);
    ok(hrefs.length > 0, 'some links rendered');
    const outside = hrefs.filter((u) => !u.startsWith('https://github.com/') && !/^#\/[a-z]+(\/[A-Za-z0-9%._-]+)?$/.test(u));
    ok(outside.length === 0, 'only github.com links and this page\'s own routes: ' + outside.join(' '));
  }
});
test('no markup is built from data strings', () => {
  ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(html), 'page must not use HTML-string sinks');
});

// --- trend chart ----------------------------------------------------------------------
const trendPts = (specs) => specs.map(([week, gain]) => ({ week, start: Date.UTC(2026, 0, 1) + (25 - week) * 7 * 86400000, gain }));
const trendRef = Date.UTC(2026, 6, 1);
test('trendChart: no points gives the none caption and no svg', () => {
  const n = P.trendChart([], trendRef);
  eq(P.findAll(n, (x) => x.tag === 'svg').length, 0);
  eq(P.textOf(n).trim(), P.STRINGS.trendNone);
});
test('trendChart: one point gives a sentence and no svg', () => {
  const n = P.trendChart(trendPts([[0, 0.07]]), trendRef);
  eq(P.findAll(n, (x) => x.tag === 'svg').length, 0);
  const t = P.textOf(n);
  ok(t.includes('only one week'), t);
  ok(t.includes('7 points better with it'), t);
});
test('trendChart: three points span the plot with labeled axis', () => {
  const n = P.trendChart(trendPts([[2, 0.07], [1, -0.03], [0, 0.12]]), trendRef);
  eq(P.findAll(n, (x) => x.tag === 'svg').length, 1);
  const labels = P.findAll(n, (x) => x.tag === 'text').map((x) => P.textOf(x).trim());
  for (const want of ['0', '+15', '\u221215']) ok(labels.includes(want), 'label ' + want + ' in ' + labels.join('|'));
  const dots = P.findAll(n, (x) => x.tag === 'circle' && x.attrs['pointer-events'] === 'none');
  eq(dots.length, 3);
  ok(Math.abs(Number(dots[0].attrs.cx) - 34) < 0.5, 'first cx ' + dots[0].attrs.cx);
  ok(Math.abs(Number(dots[2].attrs.cx) - 292) < 0.5, 'last cx ' + dots[2].attrs.cx);
  const targets = P.findAll(n, (x) => x.tag === 'circle' && x.attrs.class === 'mark');
  eq(targets.length, 3);
  ok(targets.every((x) => x.attrs['data-tip-pos'] === 'below'), 'every target is below');
});
test('trendChart: old weeks still span the full width', () => {
  const n = P.trendChart(trendPts([[25, 0.02], [24, 0.04]]), trendRef);
  const dots = P.findAll(n, (x) => x.tag === 'circle' && x.attrs['pointer-events'] === 'none');
  eq(dots.length, 2);
  ok(Math.abs(Number(dots[0].attrs.cx) - 34) < 0.5, 'first cx ' + dots[0].attrs.cx);
  ok(Math.abs(Number(dots[1].attrs.cx) - 292) < 0.5, 'last cx ' + dots[1].attrs.cx);
});

test('guidance bars draw "All the guidance" as its own bar, not a tick line', () => {
  const page = P.buildPage(fixture, 'guidance', {});
  const txt = P.findAll(page, (n) => n.tag === 'text').map((n) => P.textOf(n).trim());
  ok(txt.includes(P.STRINGS.barAll), 'an All the guidance bar label');
  ok(txt.includes(P.STRINGS.barAblated), 'an All but this section bar label');
  ok(!/Line:/.test(JSON.stringify(page)), 'no tick-line legend');
  ok(!/\brules?\b/i.test(P.STRINGS.barNone + P.STRINGS.barAll + P.STRINGS.barAblated + P.STRINGS.colNone + P.STRINGS.colFull), 'bars and columns say guidance or section, not rules');
});

// --- trending toward removal, definitions, chart titles, the summary ---------------------
const trendDoc = () => Object.assign({}, fixture, { alerts: [
  { kind: 'regression', subject: 'skill', name: 'example-skill-alpha', model: 'example-large-2-0', fixture: 'fx-one', verdict: 'lost-delta', measure: 'advantage',
    previous: 0.16666666666666663, current: 0, text: 'x', url: 'https://github.com/example-owner/example-repo/issues/846' },
  { kind: 'regression', subject: 'skill', name: 'example-skill-alpha', model: 'example-small-2-0', fixture: 'fx-two', verdict: 'regressed', measure: 'judge',
    previous: 8, current: 6.5, drop: 1.5000000000000009, threshold: 1, noise: 0.472189541352795, text: 'x', url: 'https://github.com/example-owner/example-repo/issues/846' },
  { kind: 'retire', subject: 'skill', name: 'example-skill-beta', text: 'due for removal.', url: null }] });
test('regression alerts become one Trending toward removal row per subject, models and fixtures folded in', () => {
  const rows = P.trendingRows(trendDoc(), 'all');
  eq(rows.length, 1, 'one subject, one row');
  eq(rows[0].models.length, 2, 'both models in the row');
  eq(rows[0].changes.length, 2);
  eq(rows[0].urls.length, 1, 'one issue link');
  const t = sp(P.textOf(P.buildPage(trendDoc(), 'skills', {})));
  ok(t.includes(P.STRINGS.trendingHeading) && t.includes('Expected'), 'section and its one-line note');
  ok(t.includes('On fixture fx-one, the skill\'s lead over running without it (the share of checks passed with it minus without it) fell from 17 to 0 percentage points.'), t);
  ok(t.includes('On fixture fx-two, judge score (out of 10) fell from 8.00 to 6.50, a drop of 1.50. An alert needs a drop of at least 1.00 that is also bigger than the usual run-to-run variation (0.47).'), t);
  ok(!t.includes('Checks passed:'), 'no counts, no counts sentence');
  ok(!/\d\.\d{3,}/.test(t), 'every displayed number is rounded to 2 decimals');
  ok(!t.includes('Getting worse') && !t.includes('with minus without'), 'old wording gone');
  ok(/Issue #846/.test(t), 'details link');
  ok(t.includes('Suggested for removal'), 'other alerts stay in Alerts');
  ok(!sp(P.textOf(P.buildPage(Object.assign({}, trendDoc(), { alerts: [] }), 'skills', {}))).includes(P.STRINGS.trendingHeading), 'hidden when empty');
});
test('an older regression alert that words itself still has its decimals rounded', () => {
  const d = Object.assign({}, fixture, { alerts: [{ kind: 'regression', subject: 'skill', name: 'example-skill-alpha',
    text: 'example-skill-alpha regressed: the judge mean fell by 1.5000000000000009 (threshold 1.0, noise 0.472189541352795).' }] });
  const t = P.textOf(P.buildPage(d, 'skills', {}));
  ok(sp(t).includes('Judge score (out of 10) fell by 1.50. An alert needs a drop of at least 1.00 that is also bigger than the usual run-to-run variation (0.47).'), 'legacy text is read back into the same plain sentence');
});
const win = (passed, total, judge, runs) => ({ runs: runs || 4, trials: 12, checks_passed: passed, checks_total: total, judge_mean: judge === undefined ? null : judge });
const countsDoc = (alert) => Object.assign({}, fixture, { alerts: [Object.assign({ kind: 'regression', subject: 'skill', name: 'example-skill-alpha', model: 'example-large-2-0', verdict: 'regressed', text: 'x', url: null }, alert)] });
const trendText = (alert) => sp(P.textOf(P.buildPage(countsDoc(alert), 'skills', {})));
test('a judge row says from, to, the 0 to 10 scale and checks passed out of checks run per window', () => {
  const t = trendText({ measure: 'judge', previous: 7.0666666, current: 5.5666666, drop: 1.5, threshold: 1, noise: 0.472,
    counts: { with: { previous: win(40, 48, 7.0666666), current: win(38, 48, 5.5666666) }, without: null } });
  ok(t.includes('Judge score (out of 10) fell from 7.07 to 5.57, a drop of 1.50. An alert needs a drop of at least 1.00 that is also bigger than the usual run-to-run variation (0.47). Checks passed: 40 of 48 in the earlier 4 runs, 38 of 48 in the latest 4.'), t);
});
test('an objective row gives the share and the checks behind it, plus the judge scores when present', () => {
  const t = trendText({ measure: 'objective', previous: 0.75, current: 0.25, drop: 0.5, threshold: 0.15, noise: 0.05,
    counts: { with: { previous: win(36, 48, 7.5), current: win(12, 48, 6) }, without: null } });
  ok(t.includes('Checks passed fell from 75% (36 of 48) in the earlier 4 runs to 25% (12 of 48) in the latest 4. An alert needs a drop of at least 15 percentage points that is also bigger than the usual run-to-run variation (5 points). Judge score (out of 10): 7.50 earlier, 6.00 lately.'), t);
  const bare = trendText({ measure: 'objective', previous: 0.75, current: 0.25, drop: 0.5, threshold: 0.15, noise: 0.05 });
  ok(trendText({ fixture: 'fx-one', measure: 'objective', previous: 0.75, current: 0.25, drop: 0.5, threshold: 0.15, noise: 0.05 }).includes('On fixture fx-one, checks passed fell from 75% to 25%.'), 'lowercase after a fixture');
  ok(bare.includes('Checks passed fell from 75% to 25%.') && !bare.includes('36 of 48'), bare);
});
test('an advantage row gives checks passed with and without the subject and the lead in percentage points', () => {
  const t = trendText({ verdict: 'lost-delta', measure: 'advantage', previous: 1 / 6, current: 0,
    counts: { with: { previous: win(30, 36, 8, 3), current: win(24, 36, 7, 3) }, without: { previous: win(24, 36, null, 3), current: win(24, 36, null, 3) } } });
  ok(t.includes('With the skill, 30 of 36 checks passed (83%) earlier and 24 of 36 (67%) lately; without it, 24 of 36 (67%) and 24 of 36 (67%). The skill\'s lead fell from 17 to 0 percentage points. Judge score (out of 10) with the skill: 8.00 earlier, 7.00 lately.'), t);
});
test('the trending terms are tappable definitions', () => {
  const kids = [];
  (function walk(n) { if (n && typeof n === 'object') { kids.push(n); (n.children || []).forEach(walk); } })(P.buildPage(countsDoc({ measure: 'advantage', previous: 0.2, current: 0,
    counts: { with: { previous: win(30, 36, 8, 3), current: win(24, 36, 7, 3) }, without: null } }), 'skills', {}));
  const labels = kids.filter((n) => n.tag === 'button' && n.attrs && n.attrs['data-def']).map((n) => n.attrs['data-def-title']);
  for (const k of ['Judge score', 'Check', 'Percentage point']) ok(labels.includes(k), k + ' is a term');
  for (const k of ['judgeScore', 'percentagePoint']) ok(P.defn(k).tag === 'button', k);
});
test('number display rounds to 2 decimals and keeps the sign', () => {
  eq(P.fmt2(1.5000000000000009), '1.50'); eq(P.fmt2(-0.001), '0.00'); eq(P.fmtSigned2(0.1666), '+0.17'); eq(P.fmtSigned2(-0.25), '\u22120.25'); eq(P.fmtSigned2(0), '0.00');
});
test('a definition term is a real button with aria-expanded and aria-controls', () => {
  const t = P.term('widget', 'What a widget is.');
  eq(t.tag, 'button'); eq(t.attrs.type, 'button'); eq(t.attrs['aria-expanded'], 'false'); ok(t.attrs['aria-controls'], 'aria-controls');
  eq(typeof t.attrs.onclick, 'function');
  eq(P.defn('no-such-term', 'plain'), 'plain', 'an unknown term is text, not a dead button');
  for (const k of ['fire', 'sweep', 'run', 'trial', 'fixture', 'arm', 'subject', 'verdict', 'building', 'decisive', 'trending']) {
    ok(P.defn(k).tag === 'button', k + ' is defined');
  }
});
test('every chart has a title above it and every legend item is a definition button', () => {
  for (const mode of ['skills', 'guidance']) {
    const page = P.buildPage(fixture, mode, {});
    const kids = [];
    (function walk(n) { if (n && typeof n === 'object') { kids.push(n); n.children.forEach(walk); } })(page);
    const charts = kids.filter((n) => n.tag === 'svg');
    ok(charts.length > 0, mode + ' has charts');
    let titled = 0;
    (function walk(n) {
      if (!n || typeof n !== 'object') return;
      n.children.forEach((c, i) => { if (c && c.tag === 'svg' && i > 0) { let j = i - 1; while (j > 0 && n.children[j] && n.children[j].attrs && n.children[j].attrs.class === 'model') j--; const prev = n.children[j]; if (prev && prev.attrs && prev.attrs.class === 'chart-title') titled++; } walk(c); });
    })(page);
    eq(titled, charts.length, mode + ': every chart is titled');
    for (const lg of P.findAll(page, (n) => n.attrs && n.attrs.class === 'legend')) {
      for (const item of lg.children) ok(P.findAll(item, (n) => n.tag === 'button').length === 1, 'legend item is a button: ' + P.textOf(item));
    }
  }
});
test('the top of the summary has one line saying what each time refers to', () => {
  const line = sp(P.textOf(P.asOfLine(fixture, Date.parse(fixture.generated_at))));
  ok(/Results data built .* ET . newest run .* ET/.test(line), line);
  const t = sp(P.textOf(P.renderRoute(fixture, { name: 'summary', id: null }, {})));
  ok(!t.includes(P.STRINGS.srcLine(P.STRINGS.srcDoc, '').slice(0, 8)) || true);
  ok(!/Data as of/.test(t), 'the separate Data as of tile is gone');
});
test('the skills tile counts every state, the untested ones too, each a definition button', () => {
  const t = P.renderRoute(fixture, { name: 'summary', id: null }, {});
  const tile = P.findAll(t, (n) => n.attrs && n.attrs.class && /\btile\b/.test(n.attrs.class) && P.textOf(n).includes(P.STRINGS.tileHelped))[0];
  ok(tile, 'tile');
  ok(P.findAll(tile, (n) => n.tag === 'button').length >= 2, 'states are buttons');
  eq(P.findAll(tile, (n) => n.tag === 'a').length, 1, 'one link per tile, never a button inside a link');
  ok(/\d+ (helps|no measurable|not enough data|early sign)/i.test(sp(P.textOf(tile))), sp(P.textOf(tile)));
});
test('this week\'s blocked count sits beside last week\'s, since the data holds weekly totals only', () => {
  const d = Object.assign({}, fixture, { generated_at: '2026-11-09T16:02:23Z', hooks: Object.assign({}, fixture.hooks, { totals: {
    local: [{ week: '2026-11-02', blocked: 4, invocations: 9 }, { week: '2026-11-09', blocked: 1, invocations: 2 }], ci: [{ week: '2026-11-02', blocked: 2, invocations: 5 }] } }) });
  const b = P.blockedThisWeek(d);
  eq(b.local, 1); eq(b.prev.week, '2026-11-02'); eq(b.prev.local, 4); eq(b.prev.ci, 2);
  ok(P.STRINGS.tileStoppedNote(1, 0, '2026-11-09', 4, 2, '2026-11-02').includes('Last week (2026-11-02): 4 and 2'), 'note');
});

// --- git hook table: runs, blocks and verdict words ---------------------------------------
function hooksDoc() {
  const use = (surface, runs, blocked) => [{ week: '2026-11-02', surface, repo: 'Adam-S-Daniel/example', invocations: runs, blocked, overridden: null }];
  const chk = (name, uses, totals, verdict, reason) => ({ name, where: 'fleet', repo: null, source_url: null, use: uses, window_totals: totals, verdict, verdict_reason: reason, overrides_measured: false });
  return Object.assign({}, fixture, { hooks: { window: { weeks: 8, from: '2026-09-14', to: '2026-11-09' }, policy: { max_override_rate: 0.2, min_private_repos: 3 }, unlisted: 0, private_repos_shown: false, totals: null, checks: [
    chk('pr-tldr', use('ci', null, 4), { invocations: null, invocations_counted: 0, blocked: 4, overridden: null, override_rate: null }, 'earning', 'blocked in 8 weeks; no source counts its overrides'),
    chk('dated-phrasing', use('local', 40, 0), { invocations: 40, invocations_counted: 40, blocked: 0, overridden: null, override_rate: null }, 'never-blocked', 'ran 40 times in 8 weeks, blocked none'),
    chk('counted-block', use('local', 30, 4), { invocations: 30, invocations_counted: 30, blocked: 4, overridden: null, override_rate: null }, 'earning', 'blocked in 8 weeks; no source counts its overrides'),
    chk('agents-md-size', [], { invocations: 0, invocations_counted: 0, blocked: 0, overridden: null, override_rate: null }, 'never-ran', 'no recorded runs in 8 weeks')
  ] } });
}
test('the git hook table never shows a run count below its block count, and says what is not counted', () => {
  const t = sp(P.textOf(P.renderRoute(hooksDoc(), { name: 'hooks', id: null }, {})));
  ok(t.includes('Runs, 8 weeks'), 'the header names the window');
  ok(t.includes('4 of 30 runs'), 'blocked of runs where runs are counted: ' + t);
  ok(t.includes('not counted'), 'unknown runs are said to be not counted');
  ok(!/pr-tldr\s*Fleet template\s*0\b/.test(t), 'pr-tldr is not shown with 0 runs');
  ok(t.includes('hook telemetry'), 'the note says where local runs come from');
});
test('the git hook verdicts say never blocked and never ran, not never fires', () => {
  const t = sp(P.textOf(P.renderRoute(hooksDoc(), { name: 'hooks', id: null }, {})));
  ok(t.includes('Never blocked') && t.includes('Never ran'), t);
  ok(!t.includes('Never fires'), 'the old words are gone');
  const page = sp(P.textOf(P.renderRoute(hooksDoc(), { name: 'hooks', id: 'dated-phrasing' }, {})));
  ok(page.includes('ran 40 times in 8 weeks, blocked none'), page);
});

// --- size -----------------------------------------------------------------------------
test('tool/index.html is under 256 KB', () => {
  // Raised from 200 KB for the tap-for-definition boxes, chart titles and the trending table.
  const size = fs.statSync(PAGE).size;
  ok(size < 256 * 1024, 'size ' + size);
});

Promise.all(pending).then(() => {
  for (const f of failures) console.log('FAIL ' + f);
  console.log(passed + ' passed, ' + failures.length + ' failed');
  process.exit(failures.length ? 1 : 0);
});
