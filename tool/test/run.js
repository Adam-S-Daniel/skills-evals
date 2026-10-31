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
  eq(s, 'With this skill, Example Model 1.0 passed 24 of 27 checks; without it, 15 of 27. Tried 9 times, last on Oct 31.');
});

test('guidance sentence includes the ablation clause', () => {
  const runs = [secRun('example-model-1-0', 1, 7, 4, 7, 5, 8)];
  const s = P.sentenceFor(P.poolRuns(runs, 'guidance', refMs, []), 'guidance', refMs);
  eq(s, 'With this section, Example Model 1.0 passed 7 of 8 checks; without it, 4 of 8. '
    + 'With all the rules, 7 of 8; with all the other rules but not this one, 5 of 8. Tried 3 times, last on Oct 30.');
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
  const runs = [0, 1, 2].map((d) => skillRun('a', d, 21, 20, 20 * 1)).map((r) => Object.assign(r, { with: arm(11, 20), without: arm(10, 20) }));
  eq(chipOf(runs, 'skills'), 'helps', 'exactly +0.05');
  const mixed = runs.concat([0, 1, 2].map((d) => Object.assign(skillRun('b', d, 0, 0, 20), { with: arm(9, 20), without: arm(10, 20) })));
  eq(chipOf(mixed, 'skills'), 'helps', '+0.05 and -0.05 is still helps');
});
test('chip: No measurable difference when the gain is small', () => {
  const runs = [0, 1, 2].map((d) => Object.assign(skillRun('a', d, 0, 0, 100), { with: arm(54, 100), without: arm(50, 100) }));
  eq(chipOf(runs, 'skills'), 'none');
});
test('chip: a model worse beyond 5 points blocks Helps', () => {
  const a = [0, 1, 2].map((d) => skillRun('a', d, 9, 3, 9));
  const b = [0, 1, 2].map((d) => Object.assign(skillRun('b', d, 0, 0, 100), { with: arm(40, 100), without: arm(50, 100) }));
  eq(chipOf(a.concat(b), 'skills'), 'none');
});
test('chip: Getting worse when a regression alert names it', () => {
  eq(chipOf([skillRun('a', 0, 9, 0, 9)], 'skills', true), 'worse');
  ok(P.hasRegression(fixture.alerts, 'skill', 'example-skill-delta'), 'fixture regression found');
  ok(!P.hasRegression(fixture.alerts, 'guidance', 'example-skill-delta'), 'subject must match');
});
test('chip: guidance Helps when the section also helps with the other rules present', () => {
  const runs = [0, 1, 2].map((d) => secRun('a', d, 7, 3, 7, 4, 8));
  eq(chipOf(runs, 'guidance'), 'helps');
});
test('chip: guidance Helps only on its own', () => {
  const runs = [0, 1, 2].map((d) => secRun('a', d, 7, 3, 7, 7, 8));
  eq(chipOf(runs, 'guidance'), 'alone');
  // without enough ablation runs, the second rule cannot fire
  eq(chipOf([0, 1, 2].map((d) => secRun('a', d, 7, 3, d === 0 ? 7 : null, d === 0 ? 7 : null, 8)), 'guidance'), 'helps');
});
test('chip: the guidance subject applies the shared rules too', () => {
  eq(chipOf([secRun('a', 0, 7, 3, 7, 7, 8)], 'guidance'), 'early');
  eq(chipOf([0, 1, 2].map((d) => secRun('a', d, 5, 5, 5, 5, 8)), 'guidance'), 'none');
  eq(chipOf([secRun('a', 0, 5, 5, 5, 5, 8)], 'guidance', true), 'worse');
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
  const rank = ['helps', 'early', 'none', 'insufficient', 'worse'];
  items.forEach((it, i) => {
    if (i === 0) return;
    const p = items[i - 1];
    const rp = rank.indexOf(p.chip), rc = rank.indexOf(it.chip);
    ok(rp < rc || (rp === rc && (p.pooled.all.gain === null ? it.pooled.all.gain === null
      : it.pooled.all.gain === null || p.pooled.all.gain >= it.pooled.all.gain)), 'order at ' + it.name);
  });
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
  const withGain = byValue.filter((id) => ['security', 'anything-you-name-gets-its-link', 'git-practices'].includes(id));
  eq(withGain.join(','), 'security,anything-you-name-gets-its-link,git-practices');
  const bySize = P.sectionItems(fixture, 'size').map((i) => i.bytes);
  ok(bySize.every((b, i) => i === 0 || bySize[i - 1] >= b), 'size order descending');
});
test('whole-guidance headline pools full vs none', () => {
  const w = P.wholeGuidance(fixture);
  eq(w.chip, 'helps');
  ok(w.sentence.startsWith('With all the rules, Example Large 2.0 passed'), w.sentence);
});

// --- failure states ---------------------------------------------------------
const mode = 'skills';
test('failure state when the fetch fails', async () => {
  const res = await P.loadData(P.DEFAULT_DATA_URL, () => Promise.reject(new Error('offline')), 1);
  eq(res.ok, false); eq(res.kind, 'fetch');
  const t = P.textOf(P.buildFailure(res, mode));
  ok(t.includes(P.STRINGS.failFetch), 'says it could not load');
  ok(t.includes('explorer/latest.json'), 'names the file');
  ok(t.includes('What to do'), 'says what to do');
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
test('default mode is skills; ?subject=guidance is guidance', () => {
  eq(P.modeFromSearch(''), 'skills');
  eq(P.modeFromSearch('?foo=1'), 'skills');
  eq(P.modeFromSearch('?subject=guidance'), 'guidance');
  eq(P.searchForMode('?data=x', 'guidance'), '?data=x&subject=guidance');
  eq(P.searchForMode('?subject=guidance', 'skills'), '');
});
test('each mode renders its own views', () => {
  const s = P.textOf(P.buildPage(fixture, 'skills', {}));
  ok(s.includes(P.STRINGS.skillsHeading) && !s.includes(P.STRINGS.wholeHeading), 'skills view');
  const g = P.textOf(P.buildPage(fixture, 'guidance', {}));
  ok(g.includes(P.STRINGS.wholeHeading) && g.includes(P.STRINGS.sectionsHeading), 'guidance view');
  ok(g.includes('About 150 words'), 'section size in words');
  ok(g.includes(P.GLOSSES['security']), 'gloss on the card');
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

// --- privacy ----------------------------------------------------------------------
test('no @, /home/ or cse_ string from the data reaches rendered text', () => {
  for (const m of ['skills', 'guidance']) {
    const page = P.buildPage(fixture, m, {});
    const t = P.textOf(page);
    for (const bad of ['@', '/home/', 'cse_']) ok(!t.includes(bad), m + ' mode text contains ' + bad);
    const hrefs = P.findAll(page, (n) => n.tag === 'a').map((n) => n.attrs.href);
    ok(hrefs.length > 0, 'some links rendered');
    ok(hrefs.every((u) => u.startsWith('https://github.com/')), 'only github.com links: ' + hrefs.filter((u) => !u.startsWith('https://github.com/')).join(' '));
  }
});
test('no markup is built from data strings', () => {
  ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(html), 'page must not use HTML-string sinks');
});

// --- size -----------------------------------------------------------------------------
test('tool/index.html is under 200 KB', () => {
  const size = fs.statSync(PAGE).size;
  ok(size < 200 * 1024, 'size ' + size);
});

Promise.all(pending).then(() => {
  for (const f of failures) console.log('FAIL ' + f);
  console.log(passed + ' passed, ' + failures.length + ' failed');
  process.exit(failures.length ? 1 : 0);
});
