// Tests for explorer/: the dashboard adapter, the public bundle's contents and
// the build's output. Plain Node plus the pinned devDependencies, no network.
// Run: npm test   (in explorer/; exits nonzero on any failure)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as acorn from 'acorn';
import vm from 'node:vm';
import { bundle, buildPublicPage, buildPrivatePage, buildArtifactPage } from '../build.js';
import { readDashboard, dashboardSource, DATASET_ID } from '../src/adapters/dashboard.js';
import { DEFAULT_DATA_URL, DATA_URL_PREFIX, allowedDataUrl } from '../src/adapters/web.js';
import * as artifactAdapter from '../src/adapters/artifact.js';
import * as webAdapter from '../src/adapters/web.js';
import { DATA_REPO } from '../src/config.js';
import { SCHEMA_VERSION } from '../src/core/rules.js';
import { fixtureQueue } from '../src/core/fixtures.js';
import { privateSource, PRIVATE_DATASET_ID, GROUPS } from '../src/entries/private.js';
import { makeExt, attentionRows, capUse, routineHealth } from '../src/private/views.js';
import { mergePrivate } from '../src/private/merge.js';
import { rowsOf, some } from '../src/private/datasets.js';
import { renderRoute } from '../src/views/page.js';
import { agentMadeRows } from '../src/views/impact.js';
import { textOf, findAll } from '../src/core/h.js';
import { STRINGS, useVoice } from '../src/core/strings.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXPLORER = path.resolve(HERE, '..');
const REPO = path.resolve(EXPLORER, '..');
const PAGE = path.join(REPO, 'tool', 'index.html');
const PRIVATE_PAGE = path.join(REPO, 'dashboard', 'page', 'index.html');
const DATASETS = path.join(REPO, 'dashboard', 'page', 'datasets.json');
const ARTIFACT_PAGE = path.join(EXPLORER, 'dist', 'artifact', 'index.html');

let passed = 0;
const failures = [];
async function test(name, fn) {
  try { await fn(); passed += 1; } catch (e) { failures.push(name + ': ' + e.message); }
}
function eq(actual, expected, what) {
  if (actual !== expected) throw new Error((what || 'value') + ': expected ' + JSON.stringify(expected) + ', got ' + JSON.stringify(actual));
}
function ok(cond, what) { if (!cond) throw new Error(what || 'assertion failed'); }

/* A fake Dashboard runtime: dash.data(id) answers { status, data } from a
   table the test sets, dash.onData(fn) records fn, fire() calls them all. */
function fakeDash(table) {
  const listeners = [];
  const reads = [];
  return {
    table, reads, listeners,
    data(id) { reads.push(id); return Object.prototype.hasOwnProperty.call(table, id) ? table[id] : { status: 'error' }; },
    onData(fn) { listeners.push(fn); },
    fire() { listeners.forEach((fn) => fn()); }
  };
}
const doc = (extra) => Object.assign({ schema_version: SCHEMA_VERSION, generated_at: '2026-10-31T21:00:00Z', skills: [], guidance: { sections: [] } }, extra);

/* Every string a script holds as data: string literals and template text. */
function stringsIn(js) {
  const out = [];
  const ast = acorn.parse(js, { ecmaVersion: 'latest', sourceType: 'script' });
  (function walk(n) {
    if (!n || typeof n.type !== 'string') return;
    if (n.type === 'Literal' && typeof n.value === 'string') out.push(n.value);
    if (n.type === 'TemplateElement') out.push(n.value.cooked);
    for (const [k, v] of Object.entries(n)) {
      if (k === 'type') continue;
      if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v);
    }
  })(ast);
  return out;
}
/* Every identifier a script names, `dash` in `dash.data` included. */
function identifiersIn(js) {
  const out = new Set();
  const ast = acorn.parse(js, { ecmaVersion: 'latest', sourceType: 'script' });
  (function walk(n) {
    if (!n || typeof n.type !== 'string') return;
    if (n.type === 'Identifier') out.add(n.name);
    for (const [k, v] of Object.entries(n)) {
      if (k === 'type') continue;
      if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v);
    }
  })(ast);
  return out;
}
/* What a bundle leaks of the private dashboard: dataset ids (other than
   `explorer`, the one the dashboard adapter reads) held as strings, and any
   reference to the dashboard runtime. */
function privateLeaks(js) {
  const ids = Object.keys(JSON.parse(fs.readFileSync(DATASETS, 'utf8'))).filter((id) => id !== DATASET_ID);
  if (ids.length < 5) throw new Error('dashboard/page/datasets.json lists only ' + ids.length + ' datasets');
  const strings = new Set(stringsIn(js));
  const leaks = ids.filter((id) => strings.has(id)).map((id) => 'dataset id ' + id);
  if (identifiersIn(js).has('dash')) leaks.push('identifier dash');
  if (/\bdash\./.test(js)) leaks.push('text dash.');
  return leaks;
}
const inlineScripts = (html) => [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\b[^>]*>/gi)].map((m) => m[1]);

// --- dashboard adapter ---------------------------------------------------------
await test('readDashboard returns the document from the explorer dataset', () => {
  const d = doc({ newest_run: '2026-10-30T00:00:00Z' });
  const dash = fakeDash({ explorer: { status: 'ok', data: d } });
  const res = readDashboard(dash);
  eq(res.ok, true);
  eq(res.doc, d, 'the same object, unchanged');
  eq(dash.reads.join(','), 'explorer', 'reads the explorer dataset only');
});
await test('readDashboard reports loadData-shaped failures', () => {
  eq(readDashboard(fakeDash({ explorer: { status: 'loading' } })).kind, 'loading');
  eq(readDashboard(fakeDash({ explorer: { status: 'error' } })).kind, 'fetch');
  eq(readDashboard(fakeDash({})).kind, 'fetch', 'no such dataset');
  eq(readDashboard({ data() { throw new Error('runtime gone'); } }).kind, 'fetch', 'a throwing runtime');
  eq(readDashboard(fakeDash({ explorer: { status: 'ok', data: [1, 2] } })).kind, 'parse', 'rows, not a document');
  const old = readDashboard(fakeDash({ explorer: { status: 'ok', data: doc({ schema_version: 99 }) } }));
  eq(old.kind, 'schema'); eq(old.got, '99');
});
await test('dashboardSource renders now and again on every onData', () => {
  const dash = fakeDash({ explorer: { status: 'loading' } });
  const seen = [];
  dashboardSource(dash).start({ onDoc: (d, url) => seen.push(['doc', d.generated_at, url]), onFail: (r) => seen.push(['fail', r.kind]) });
  eq(dash.listeners.length, 1, 'subscribes once');
  eq(seen.length, 0, 'a loading dataset reports nothing yet');
  dash.table.explorer = { status: 'ok', data: doc() };
  dash.fire();
  dash.table.explorer = { status: 'ok', data: doc({ generated_at: '2026-11-01T00:00:00Z' }) };
  dash.fire();
  dash.table.explorer = { status: 'error' };
  dash.fire();
  eq(JSON.stringify(seen), JSON.stringify([['doc', '2026-10-31T21:00:00Z', null], ['doc', '2026-11-01T00:00:00Z', null], ['fail', 'fetch']]));
});
await test('dashboardSource reports a ready dataset at once', () => {
  const dash = fakeDash({ explorer: { status: 'ok', data: doc() } });
  let n = 0;
  dashboardSource(dash).start({ onDoc: () => { n += 1; }, onFail: () => { throw new Error('no failure expected'); } });
  eq(n, 1);
});

// --- the private build's own pieces -----------------------------------------------------
const okData = (rows) => ({ status: 'ok', data: rows });
await test('privateSource merges explorer_private in with a Private mark, and works without it', () => {
  const pub = doc({ skills: [{ name: 'example-public' }], evals: { runs: [{ id: 1 }], bare_runs: [] } });
  const priv = doc({ skills: [{ name: 'example-private' }], evals: { runs: [{ id: 2 }], bare_runs: [{ id: 3 }] } });
  const seen = [];
  const dash = fakeDash({ explorer: okData(pub), explorer_private: okData(priv) });
  privateSource(dash).start({ onDoc: (d) => seen.push(d), onFail: () => { throw new Error('no failure expected'); } });
  eq(seen.length, 1);
  eq(seen[0].skills.map((x) => x.name + ':' + (x.private === true)).join(','), 'example-public:false,example-private:true');
  eq(seen[0].evals.runs.length, 2); eq(seen[0].evals.bare_runs.length, 1);
  eq(pub.skills.length, 1, 'the public document is not changed in place');
  const alone = [];
  privateSource(fakeDash({ explorer: okData(pub), explorer_private: { status: 'loading' } })).start({ onDoc: (d) => alone.push(d), onFail: () => {} });
  eq(alone[0], pub, 'without the optional dataset the document passes through');
  eq(PRIVATE_DATASET_ID, 'explorer_private');
  eq(mergePrivate(pub, null), pub);
});
await test('placeholder rows never reach a panel, and an empty dataset hides it', () => {
  const dash = fakeDash({ waiting: okData([{ id: 'none', item: 'Nothing' }]), ci_red_runs: okData([{ key: 'none' }, { key: 'k', week: '2026-10-26' }]),
    routines: { status: 'loading' } });
  eq(rowsOf(dash, 'waiting').length, 0);
  eq(some(dash, 'waiting'), null);
  eq(rowsOf(dash, 'ci_red_runs').length, 1);
  eq(rowsOf(dash, 'routines'), null, 'loading');
  eq(rowsOf(dash, 'no_such'), null, 'missing');
  const ext = makeExt(dash);
  eq(ext.covers('red-runs'), true);
  eq(ext.covers('runs'), false, 'no run_stream: the public panel stays');
  eq(ext.covers('cost'), false);
});
await test('the Needs you list merges half-built issues, document alerts and fires without results, high first', () => {
  const dash = fakeDash({ half_built_issues: okData([{ key: 'k1', state: 'open', kind: 'partial', severity: 'low', title: 'Low one', url: 'https://github.com/example-owner/r/issues/1' },
    { key: 'k2', state: 'closed', kind: 'broken', severity: 'high', title: 'Closed', url: null }]) });
  const d = doc({ alerts: [{ kind: 'regression', name: 'example-skill', subject: 'skill', text: 'got worse' }],
    fires_without_results: { without_results: 2, rejected: 0, since: '2026-10-30T00:00:00Z', sweeps: [] } });
  const rows = attentionRows(dash, d);
  eq(rows.length, 3, 'the closed issue is left out');
  eq(rows[0].severity, 'high');
  ok(rows.map((r) => r.what).join(' | ').includes('Low one'), 'the half-built issue');
  eq(attentionRows(fakeDash({}), doc()).length, 0);
});
await test('the allowance and routine health come from their datasets', () => {
  const cap = capUse([{ points: 40.5, account_week_used: 70, pace_room_points: 3, account_reading_at: '2026-11-04T03:30:10Z', week_resets_at: '2026-11-09T17:00:00Z' }],
    [{ setting: 'weekly_cap', value: 1 }, { setting: 'stop_when_account_above', value: 0.9 }, { setting: 'per_run_cap', value: 0.01 }, { setting: 'per_run_overrun', value: 0.002 }]);
  eq(cap.spent, 40.5); eq(cap.cap, 100); eq(cap.stop, 90); eq(cap.room, 59.5);
  eq(Math.round(cap.reservation * 1000) / 1000, 1.2);
  eq(capUse(null, []), null);
  const rh = routineHealth([{ health: 'OK' }, { health: 'Stalled' }, { health: 'Retired' }, { health: 'Not run yet' }]);
  eq(JSON.stringify(rh), '{"active":2,"ok":1,"attention":1}');
});
await test('the private build has six groups, Needs you second, and speaks to "you"', () => {
  eq(GROUPS.join(','), 'summary,needs,hooks,loop,impact,ops');
  const dash = fakeDash({ waiting: okData([{ id: 'w1', item: 'Approve the example hook', where: 'example-owner/r', link: 'https://github.com/example-owner/r/pull/3', since: '2026-10-30T00:00:00Z' }]) });
  useVoice('you');
  try {
    const node = renderRoute(doc(), { name: 'needs', id: null }, { ext: makeExt(dash) });
    const t = textOf(node);
    ok(t.includes('Approve the example hook') && t.includes(STRINGS.groups.needs), t);
    ok(!/the owner/.test(t), 'no third person in the private voice');
    const hrefs = findAll(node, (n) => n.tag === 'a').map((n) => n.attrs.href);
    eq(hrefs.join(','), 'https://github.com/example-owner/r/pull/3');
  } finally { useVoice('owner'); }
  const pub = textOf(renderRoute(doc(), { name: 'needs', id: null }, {}));
  ok(!pub.includes('Approve the example hook'), 'no Needs you content without the private overlays');
});
await test('every route renders with the private overlays and every dataset empty or loading', () => {
  const ext = makeExt(fakeDash({}));
  for (const name of ['summary', 'needs', 'hooks', 'skills', 'guidance', 'removed', 'method', 'loop', 'impact', 'ops']) {
    ok(textOf(renderRoute(doc(), { name, id: null }, { ext })).length > 0, name);
  }
});

// --- made by agents (agent_made, _agent-guidance#451) ---------------------------------------
const amRow = (o) => ({ total: 0, by_origin: { agent: 0, loop: 0, person: 0, unknown: 0 }, agent_under_rule: 0, agent_verdicts: {}, ...o });
const amDoc = () => doc({ agent_made: {
  rule_since: '2026-10-26T14:40:02Z',
  items: [
    { kind: 'check', id: 'demo-check', origin: 'agent', created: '2026-10-30T00:00:00Z', commit: 'aaaaaaaaaaaa', method: 'trailer', under_rule: true, impact: { runs: 12, blocked: 3, verdict: 'blocks' } },
    { kind: 'skill', id: 'demo-skill', origin: 'agent', created: '2026-09-24T00:00:00Z', commit: 'bbbbbbbbbbbb', method: 'first-add', under_rule: false, impact: { invocations: 5, verdict: 'keep' } },
    { kind: 'section', id: 'demo-section', origin: 'person', created: '2026-08-01T00:00:00Z', commit: 'cccccccccccc', method: 'first-appearance', under_rule: false, impact: { verdict: null, current_text_runs: 0 } }],
  summary: {
    check: amRow({ total: 1, by_origin: { agent: 1, loop: 0, person: 0, unknown: 0 }, agent_under_rule: 1, agent_verdicts: { blocks: 1 }, agent_runs: 12, agent_blocked: 3 }),
    skill: amRow({ total: 1, by_origin: { agent: 1, loop: 0, person: 0, unknown: 0 }, agent_verdicts: { keep: 1 }, agent_invocations: 5 }),
    section: amRow({ total: 1, by_origin: { agent: 0, loop: 0, person: 1, unknown: 0 } }) } } });
await test('made by agents: absent is not reported', () => {
  for (const d of [doc(), doc({ agent_made: null })]) eq(agentMadeRows(d), null);
  ok(!textOf(renderRoute(doc(), { name: 'impact', id: null }, {})).includes(STRINGS.agentMade), 'no panel without the block');
});
await test('made by agents: counts by kind, agent items newest first, linked to their pages', () => {
  const r = agentMadeRows(amDoc());
  eq(r.kinds.map((k) => [k.kind, k.total, k.agent, k.afterRule].join(':')).join(','), 'check:1:1:1,skill:1:1:0,section:1:0:0');
  eq(r.kinds[0].impact, '12 runs, 3 blocked; verdicts: blocks 1');
  eq(r.items.map((i) => i.id).join(','), 'demo-check,demo-skill');
  const node = renderRoute(amDoc(), { name: 'impact', id: null }, {});
  ok(textOf(node).includes(STRINGS.agentMade), 'panel shown');
  const hrefs = findAll(node, (n) => n.tag === 'a').map((n) => n.attrs.href);
  ok(hrefs.includes('#/hooks/demo-check') && hrefs.includes('#/skills/demo-skill'), hrefs.join(' '));
  ok(!hrefs.includes('#/guidance/demo-section'), 'person-made items are counted, not listed');
});

// --- fixture requests (ported from dashboard/build.py's fixture_queue) ----------------------
const FQ_REF = Date.parse('2026-11-03T12:00:00Z');
const fqDoc = (kw) => ({ fixture_queue: Object.assign({
  schema: 1, generated_at: '2026-11-03T10:00:00Z',
  requests: [
    { issue: 11, kind: 'needs-fixtures', subject: 'demo-new', state: 'open', opened_at: '2026-11-02T12:00:00Z', closed_at: null, prs: [] },
    { issue: 12, kind: 'needs-harder-fixtures', subject: 'demo-old', state: 'open', opened_at: '2026-10-30T00:00:00Z', closed_at: null,
      prs: [{ number: 40, state: 'closed', merged_at: null }, { number: 44, state: 'merged', merged_at: '2026-11-01T00:00:00Z' }] },
    { issue: 13, kind: 'needs-trigger-set', subject: 'demo-done', state: 'closed', opened_at: '2026-10-01T00:00:00Z', closed_at: '2026-10-05T00:00:00Z', prs: [] }],
  fixtures: [
    { path: 'evals/demo-old/a', subject: 'demo-old', origin_kind: 'real-work', request: 12, runs: 4, cost_usd: 1.25 },
    { path: 'evals/demo-old/b', subject: 'demo-old', origin_kind: 'invented', request: 12, runs: 2, cost_usd: 0.5 },
    { path: 'evals/other/c', subject: 'other', origin_kind: 'invented', request: 99, runs: 7, cost_usd: 9.0 }],
  totals: { requests_open: 2, requests_closed: 1 }, findings: [] }, kw || {}) });
await test('fixture requests: null or absent is not reported', () => {
  for (const d of [{}, { fixture_queue: null }, { fixture_queue: { schema: 1 } }]) eq(fixtureQueue(d, FQ_REF), null);
});
await test('fixture requests fold in PRs and fixtures and sort open, oldest first', () => {
  const q = fixtureQueue(fqDoc(), FQ_REF);
  eq(q.rows.map((r) => r.issue).join(','), '12,11,13');
  const old = q.rows[0];
  eq([old.kind, old.subject, old.state].join('|'), 'harder fixtures|demo-old|open');
  eq(old.ageDays, 4.5, 'full precision; the view rounds');
  eq([old.prs, old.prUrl, old.merged].join('|'), '2|https://github.com/' + DATA_REPO + '/pull/44|true');
  eq([old.fixtures, old.realWork, old.runs, old.costUsd].join('|'), '2|1|6|1.75');
  eq(old.issueUrl, 'https://github.com/' + DATA_REPO + '/issues/12');
  const nw = q.rows[1];
  eq([nw.kind, nw.prs, nw.prUrl, nw.merged, nw.fixtures].join('|'), 'new fixtures|0||false|0');
  const done = q.rows[2];
  eq([done.kind, done.state, done.ageDays].join('|'), 'trigger set|closed|');
  eq(fixtureQueue(fqDoc({ findings: [{ kind: 'stuck-pr', severity: 'high' }] }), FQ_REF).findings.length, 1);
  eq(fixtureQueue(fqDoc({ requests: [], fixtures: [] }), FQ_REF).rows.length, 0);
});

// --- web adapter and config ------------------------------------------------------
await test('the data URL is built from the one DATA_REPO value', () => {
  eq(DATA_REPO, 'Adam-S-Daniel/skills-evals');
  eq(DEFAULT_DATA_URL, 'https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/persistent/eval-results/explorer/latest.json');
  eq(DATA_URL_PREFIX, 'https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals/');
  eq(allowedDataUrl(DEFAULT_DATA_URL), DEFAULT_DATA_URL);
  eq(allowedDataUrl('https://raw.githubusercontent.com/Adam-S-Daniel/skills-evals-x/main/x'), null);
});
await test('no source file but config.js names the owner/repo', () => {
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
  const files = walk(path.join(EXPLORER, 'src')).concat(walk(path.join(EXPLORER, 'template')));
  ok(files.length > 10, 'found the source files');
  const naming = files.filter((f) => fs.readFileSync(f, 'utf8').includes(DATA_REPO)).map((f) => path.relative(EXPLORER, f));
  eq(naming.join(','), path.join('src', 'config.js'));
});

// --- the public bundle -------------------------------------------------------------
const publicJs = await bundle('public.js');
const privateJs = await bundle('private.js');
await test('the leak check sees the dashboard adapter in the private bundle', () => {
  // The negative control: the same check must flag what it exists to keep out.
  const leaks = privateLeaks(privateJs);
  ok(leaks.includes('identifier dash') && leaks.includes('text dash.'), 'private bundle leaks: ' + leaks.join('; '));
  ok(stringsIn(privateJs).includes(DATASET_ID), 'the private bundle reads the explorer dataset');
});
await test('the public bundle holds no private dataset id and no dash reference', () => {
  eq(privateLeaks(publicJs).join('; '), '');
});
await test('the committed page holds no private dataset id and no dash reference', () => {
  const scripts = inlineScripts(fs.readFileSync(PAGE, 'utf8'));
  eq(scripts.length, 1, 'one inline script');
  eq(privateLeaks(scripts[0]).join('; '), '');
});
await test('the public bundle leaves out the dashboard adapter, the private entry and every private view', () => {
  // The negative control: the private bundle carries the same markers.
  for (const m of ['src/adapters/dashboard.js', 'src/entries/private.js', 'src/private/views.js', 'src/private/strings.js']) {
    ok(privateJs.includes(m), 'the private bundle names ' + m);
    ok(!publicJs.includes(m), 'the public bundle names ' + m);
  }
  const privateOnly = ['Waiting on you', 'Half-built and broken features'];
  for (const t of privateOnly) {
    ok(stringsIn(privateJs).some((x) => x.includes(t)), 'the private bundle holds ' + t);
    ok(!stringsIn(publicJs).some((x) => x.includes(t)), 'the public bundle holds ' + t);
  }
  ok(!stringsIn(publicJs).includes(DATASET_ID), 'no explorer dataset id');
});

await test('the leak check counts explorer_private as private', () => {
  ok(Object.keys(JSON.parse(fs.readFileSync(DATASETS, 'utf8'))).includes(PRIVATE_DATASET_ID));
  ok(privateLeaks(privateJs).includes('dataset id ' + PRIVATE_DATASET_ID), 'the private bundle names it');
});

// --- the built page ------------------------------------------------------------------
await test('tool/index.html is a fresh build of explorer/src', async () => {
  const fresh = await buildPublicPage();
  ok(fresh === fs.readFileSync(PAGE, 'utf8'), 'tool/index.html differs from a build: run `npm run build` in explorer/ and commit both');
});
await test('tool/index.html is one self-contained file', () => {
  const html = fs.readFileSync(PAGE, 'utf8');
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html), 'no external script');
  ok(!/<link\b/i.test(html), 'no linked stylesheet or other resource');
  ok(!/@import\b/.test(html), 'no CSS import');
  eq((html.match(/<style>/g) || []).length, 1, 'one inline style block');
  ok(html.includes(DEFAULT_DATA_URL), 'the noscript text names the data file');
  ok(!html.includes('{{') && !html.includes('__BUNDLE__'), 'no template marker left');
});

await test('dashboard/page/index.html is a fresh build of explorer/src', async () => {
  const fresh = await buildPrivatePage();
  ok(fresh === fs.readFileSync(PRIVATE_PAGE, 'utf8'), 'dashboard/page/index.html differs from a build: run `npm run build` in explorer/ and commit both');
});
await test('dashboard/page/index.html is one self-contained Dashboard fragment', () => {
  const html = fs.readFileSync(PRIVATE_PAGE, 'utf8');
  ok(html.startsWith('<style>'), 'starts with its style block');
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html) && !/<link\b/i.test(html) && !/@import\b/.test(html), 'nothing loaded from elsewhere');
  eq((html.match(/<style>/g) || []).length, 1, 'one inline style block');
  eq(inlineScripts(html).length, 1, 'one inline script');
  ok(!html.includes('{{') && !html.includes('__BUNDLE__') && !html.includes('__CSS__'), 'no template marker left');
  ok(!/<html|<body|<!doctype/i.test(html), 'a fragment, not a document: the Dashboard wraps it');
  ok(!/\bAdam(?:'s|\s)/.test(html), 'names no person (the repository owner/name aside)');
});

await test('both pages paint the whole window in the theme color, not only their column', () => {
  // Regression: the dark private page showed a white frame outside the column and below short pages.
  const pub = fs.readFileSync(PAGE, 'utf8'), priv = fs.readFileSync(PRIVATE_PAGE, 'utf8');
  ok(/html \{[^}]*background: var\(--page\)[^}]*min-height: 100%/.test(pub), 'public html background');
  ok(/body \{[^}]*background: var\(--page\)[^}]*min-height: 100vh/.test(pub), 'public body background');
  ok(/html, body \{ background: var\(--color-bg, #FDFBF7\); \}/.test(priv), 'private light background');
  ok(/prefers-color-scheme: dark\) \{ html, body \{ background: var\(--color-bg, #1E1C19\); \} \}/.test(priv), 'private dark background');
  ok(/body \{ min-height: 100vh; \}/.test(priv), 'private body fills the window');
});

// --- the artifact build -------------------------------------------------------------
// dist/artifact/index.html is published as a claude.ai artifact with latest.json
// beside it; the artifact's CSP is connect-src 'self' blob:, so it must read only
// that relative file.
const artifactJs = await bundle('artifact.js');
/* The page's EXPORTS, run in a Node sandbox as tool/test/run.js does. */
function exportsOf(js) {
  const sandbox = { module: { exports: {} }, URL, URLSearchParams, Intl, console, Date, Math, JSON };
  vm.runInNewContext(js, sandbox, { filename: 'bundle.js' });
  return sandbox.module.exports;
}
/* Every fetch-like call whose first argument is a string or template literal. */
function literalFetches(js) {
  const out = [];
  const ast = acorn.parse(js, { ecmaVersion: 'latest', sourceType: 'script' });
  (function walk(n) {
    if (!n || typeof n.type !== 'string') return;
    if (n.type === 'CallExpression') {
      const c = n.callee;
      const name = c.type === 'Identifier' ? c.name : (c.type === 'MemberExpression' && c.property.type === 'Identifier' ? c.property.name : '');
      const a = n.arguments[0];
      if (/^(fetch|fetchFn|sendBeacon|open)$/.test(name) && a && (a.type === 'Literal' || a.type === 'TemplateLiteral')) out.push(name);
    }
    for (const [k, v] of Object.entries(n)) {
      if (k === 'type') continue;
      if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v);
    }
  })(ast);
  return out;
}
await test('the artifact adapter exports what the web adapter exports, and reads latest.json only', async () => {
  eq(Object.keys(artifactAdapter).sort().join(','), Object.keys(webAdapter).filter((k) => k !== 'DATA_URL_PREFIX').sort().join(','));
  eq(artifactAdapter.DEFAULT_DATA_URL, 'latest.json');
  eq(artifactAdapter.allowedDataUrl(DEFAULT_DATA_URL), null, 'no override, not even the public file');
  eq(artifactAdapter.allowedDataUrl('http://localhost:8080/latest.json'), null);
  eq(JSON.stringify(artifactAdapter.dataUrlFromSearch('?data=' + encodeURIComponent(DEFAULT_DATA_URL))), '{"url":"latest.json"}');
  const asked = [];
  const fakeFetch = async (u) => { asked.push(u); return { ok: true, json: async () => doc() }; };
  const seen = await new Promise((resolve) => artifactAdapter.webSource(fakeFetch, '?data=https://example.com/x.json', 7)
    .start({ onDoc: (d, url) => resolve(['doc', url]), onFail: (r) => resolve(['fail', r.kind]) }));
  eq(seen.join(','), 'doc,latest.json');
  eq(asked.join(','), 'latest.json?v=7', 'one relative, cache-busted read; the ?data override is ignored');
});
// Whether a bundle's text names the raw GitHub content host anywhere. This scans
// built code for a string; it is not URL validation, so it counts occurrences
// rather than matching a URL.
const namesRawHost = (text) => text.split('raw.githubusercontent.com').length > 1;
await test('the artifact bundle names no raw.githubusercontent.com URL', () => {
  // The negative control: the public bundle does.
  ok(namesRawHost(publicJs), 'the public bundle names raw.githubusercontent.com');
  ok(!namesRawHost(artifactJs), 'the artifact bundle names raw.githubusercontent.com');
  ok(!artifactJs.includes('src/adapters/web.js') && artifactJs.includes('src/adapters/artifact.js'), 'web.js is replaced by artifact.js');
  const dataFiles = stringsIn(artifactJs).filter((x) => /\.json(\?|#|$)/.test(x));
  eq([...new Set(dataFiles)].join(','), 'latest.json', 'the one data file it names');
});
await test('the artifact bundle fetches no literal URL and reads the data through one relative path', () => {
  // The negative control: the check sees a literal absolute fetch.
  eq(literalFetches("fetch('https://example.com/x.json');").join(','), 'fetch');
  eq(literalFetches(artifactJs).join(','), '');
  const E = exportsOf(artifactJs);
  eq(E.DEFAULT_DATA_URL, 'latest.json');
  eq(JSON.stringify(E.dataUrlFromSearch('?data=http://localhost/x.json')), '{"url":"latest.json"}');
  eq(E.allowedDataUrl('https://raw.githubusercontent.com/' + DATA_REPO + '/main/x.json'), null);
});
await test('the artifact bundle holds no private code, dataset id or dash reference', () => {
  eq(privateLeaks(artifactJs).join('; '), '');
  for (const m of ['src/adapters/dashboard.js', 'src/entries/private.js', 'src/private/views.js', 'src/private/strings.js']) {
    ok(privateJs.includes(m) && !artifactJs.includes(m), 'the artifact bundle names ' + m);
  }
  for (const t of ['Waiting on you', 'Half-built and broken features']) {
    ok(!stringsIn(artifactJs).some((x) => x.includes(t)), 'the artifact bundle holds ' + t);
  }
  ok(!stringsIn(artifactJs).includes(DATASET_ID), 'no explorer dataset id');
});
await test('the artifact entry boots exactly as the public one, with the artifact adapter', () => {
  // Parsed, not compared as text: positions and comments aside, the two entries
  // are the same program once the adapter import is read as web.js.
  const shape = (file, from, to) => JSON.stringify(acorn.parse(fs.readFileSync(path.join(EXPLORER, 'src', 'entries', file), 'utf8'),
    { ecmaVersion: 'latest', sourceType: 'module' }), (k, v) => (k === 'start' || k === 'end' || k === 'raw') ? undefined : (v === from ? to : v));
  const pub = shape('public.js'), art = shape('artifact.js', '../adapters/artifact.js', '../adapters/web.js');
  ok(pub !== shape('private.js'), 'the comparison can tell two entries apart');
  ok(art === pub, 'entries/artifact.js differs from entries/public.js beyond its adapter import');
});
await test('the artifact page exposes the public page\'s functions, and no dashboard runtime', () => {
  const pub = exportsOf(publicJs), art = exportsOf(artifactJs);
  eq(Object.keys(art).sort().join(','), Object.keys(pub).sort().join(','));
  ok(!Object.keys(art).includes('readDashboard') && !Object.keys(art).includes('privateSource'), 'no dashboard adapter');
});
await test('explorer/dist/artifact/index.html is a fresh, self-contained build', async () => {
  ok(fs.existsSync(ARTIFACT_PAGE), 'explorer/dist/artifact/index.html is missing: run `npm run build` in explorer/');
  const html = fs.readFileSync(ARTIFACT_PAGE, 'utf8');
  ok((await buildArtifactPage()) === html, 'explorer/dist/artifact/index.html differs from a build: run `npm run build` in explorer/ and commit every page');
  ok(/^<!doctype html>/i.test(html), 'a whole document, like tool/index.html');
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html) && !/<link\b/i.test(html) && !/@import\b/.test(html), 'nothing loaded from elsewhere');
  const scripts = inlineScripts(html);
  eq(scripts.length, 1, 'one inline script');
  eq(privateLeaks(scripts[0]).join('; '), '');
  ok(!namesRawHost(html), 'the page, noscript text included, names no raw URL');
  ok(html.includes('latest.json') && !html.includes('{{') && !html.includes('__BUNDLE__'), 'the noscript names latest.json; no template marker left');
});

for (const f of failures) console.log('FAIL ' + f);
console.log(passed + ' passed, ' + failures.length + ' failed');
process.exit(failures.length ? 1 : 0);
