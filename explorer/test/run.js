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
import { judgeCell } from '../src/views/subject.js';
import { renderRoute } from '../src/views/page.js';
import { agentMadeRows } from '../src/views/impact.js';
import { conversionTotals, conversionView, conversionBody, PLANNER_CHANGE } from '../src/private/conversion.js';
import { utilityTotals, periodStart, inPeriod, NO_USE } from '../src/views/utility.js';
import { textOf, findAll } from '../src/core/h.js';
import { hashFor } from '../src/core/route.js';
import { sectionItems, skillItems } from '../src/core/items.js';
import { trendingRows } from '../src/views/trending.js';
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
await test('the Needs you list merges half-built issues, document alerts and fires without results, medium first', () => {
  const dash = fakeDash({ half_built_issues: okData([{ key: 'k1', state: 'open', kind: 'partial', severity: 'low', title: 'Low one', url: 'https://github.com/example-owner/r/issues/1' },
    { key: 'k2', state: 'closed', kind: 'broken', severity: 'high', title: 'Closed', url: null }]) });
  const d = doc({ alerts: [{ kind: 'retire', name: 'example-skill', subject: 'skill', text: 'due for removal' }],
    fires_without_results: { without_results: 2, rejected: 0, counted: 9, since: '2026-10-30T00:00:00Z', sweeps: [] } });
  const rows = attentionRows(dash, d);
  eq(rows.length, 3, 'the closed issue is left out');
  eq(rows[0].severity, 'medium');
  ok(rows.map((r) => r.what).join(' | ').includes('Low one'), 'the half-built issue');
  ok(rows.map((r) => r.what).join(' | ').includes('2 of 9 fires'), 'the fires line says out of how many');
  eq(attentionRows(fakeDash({}), doc()).length, 0);
});
await test('a regression alert is not a Needs attention row: it is trending toward removal, in its own table', () => {
  const d = doc({ alerts: [{ kind: 'regression', name: 'example-skill', subject: 'skill', model: 'claude-opus-5-5', fixture: 'fx-one', verdict: 'regressed', measure: 'judge',
    previous: 7.5, current: 6.0000000000000009, drop: 1.5000000000000009, threshold: 1, noise: 0.472189541352795, text: 'x', url: 'https://github.com/example-owner/r/issues/5' }] });
  eq(attentionRows(fakeDash({}), d).length, 0, 'not an attention row');
  const t = textOf(renderRoute(d, { name: 'needs', id: null }, { ext: makeExt(fakeDash({})) }));
  ok(t.includes(STRINGS.trendingHeading) && /fell from 7\.50 to 6\.00, a drop of 1\.50\.\s+An alert needs a drop of at least 1\.00/.test(t.replace(/\s+/g, ' ')), t);
  ok(!/\d\.\d{3,}/.test(t), 'no long decimal on the page: ' + t);
});
await test('a regression alert on a subject the loop decided to keep is not trending toward removal', () => {
  const reg = (name, subject) => ({ kind: 'regression', name: name, subject: subject, model: 'claude-sonnet-5-5', fixture: 'fx-one', verdict: 'regressed',
    measure: 'objective', previous: 0.75, current: 0.25, drop: 0.5, threshold: 0.15, noise: 0.31, text: name + ' regressed on fx-one.', url: 'https://github.com/example-owner/r/issues/7' });
  const d = doc({ alerts: [reg('kept-section', 'guidance'), reg('open-section', 'guidance'), reg('kept-skill', 'skill')],
    skills: [{ name: 'kept-skill', status: 'covered', verdict: 'keep', runs: [] }],
    guidance: { sections: [{ id: 'kept-section', verdict: 'keep', runs: [] }, { id: 'open-section', verdict: 'insufficient', runs: [] }] } });
  const chips = Object.fromEntries(sectionItems(d).map((s) => [s.id, s.chip]));
  eq(chips['kept-section'], 'helps', 'a kept section keeps its verdict chip');
  eq(chips['open-section'], 'worse', 'an undecided section with a regression still trends toward removal');
  eq(skillItems(d)[0].chip, 'helps', 'a kept skill keeps its verdict chip');
  eq(trendingRows(d, 'all').map((r) => r.name).join(','), 'open-section', 'only the undecided subject is in the trending table');
  const rows = attentionRows(fakeDash({}), d);
  eq(rows.length, 2, 'both kept subjects are ordinary alerts');
  ok(rows.every((r) => r.kind.includes(STRINGS.alertRegressionDecided)), JSON.stringify(rows));
  // Alerts are listed on the private dashboard's summary only.
  const t = textOf(renderRoute(d, { name: 'summary', id: null }, { ext: {} })).replace(/\s+/g, ' ');
  ok(t.includes(STRINGS.alertRegressionDecided + ': kept-section'), t);
  ok(!textOf(renderRoute(d, { name: 'summary', id: null }, {})).includes(STRINGS.alertRegressionDecided), 'the public summary lists no alerts');
  const priv = renderRoute(d, { name: 'summary', id: null }, { ext: {} });
  const alertTile = findAll(priv, (n) => n.attrs && /\btile\b/.test(n.attrs.class || '') && textOf(n).startsWith(STRINGS.tileAlerts))[0];
  ok(alertTile, 'the dashboard has an alerts tile');
  eq(findAll(alertTile, (n) => n.tag === 'a')[0].attrs.href, hashFor('needs'), 'it opens Needs you');
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
// Unminified, so the module path comments the leak checks look for survive.
const privateJs = await bundle('private.js', { minifyWhitespace: false });
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
/* The one resource a page may load: base.css's Google Fonts stylesheet. Fonts
   only change the look; every stack ends in faces readers already have. */
const FONT_IMPORT = /@import url\("https:\/\/fonts\.googleapis\.com\/css2\?[^"\s]*"\);/g;
function loadsOnlyFonts(html) {
  const imports = html.match(/@import\b/g) || [];
  const fonts = html.match(FONT_IMPORT) || [];
  const remote = (html.replace(FONT_IMPORT, '').match(/url\(\s*["']?(?!data:)(?:[a-z]+:|\/\/)/gi) || []);
  return imports.length === 1 && fonts.length === 1 && remote.length === 0;
}
await test('tool/index.html is one self-contained file', () => {
  const html = fs.readFileSync(PAGE, 'utf8');
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html), 'no external script');
  ok(!/<link\b/i.test(html), 'no linked stylesheet or other resource');
  ok(loadsOnlyFonts(html), 'no CSS import or remote url() but the one Google Fonts stylesheet');
  eq((html.match(/<style>/g) || []).length, 1, 'one inline style block');
  ok(html.includes(DEFAULT_DATA_URL), 'the noscript text names the data file');
  ok(!html.includes('{{') && !html.includes('__BUNDLE__'), 'no template marker left');
});

await test('dashboard/page/index.html is a fresh build of explorer/src', async () => {
  const fresh = await buildPrivatePage();
  ok(fresh === fs.readFileSync(PRIVATE_PAGE, 'utf8'), 'dashboard/page/index.html differs from a build: run `npm run build` in explorer/ and commit both');
});
await test('the private page fits an ArtifactData document once JSON-serialized', async () => {
  // The console stores the page as the `text` field of files/index.html, a
  // document capped at 262,144 bytes of UTF-8 after JSON.stringify.
  const page = await buildPrivatePage();
  const size = Buffer.byteLength(JSON.stringify({ text: page }), 'utf8');
  ok(size < 262144, 'serialized private page is ' + size + ' bytes, over the 262,144 limit');
});
await test('dashboard/page/index.html is one self-contained Dashboard fragment', () => {
  const html = fs.readFileSync(PRIVATE_PAGE, 'utf8');
  ok(html.startsWith('<style>'), 'starts with its style block');
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html) && !/<link\b/i.test(html) && loadsOnlyFonts(html), 'nothing loaded from elsewhere but the font stylesheet');
  eq((html.match(/<style>/g) || []).length, 1, 'one inline style block');
  eq(inlineScripts(html).length, 1, 'one inline script');
  ok(!html.includes('{{') && !html.includes('__BUNDLE__') && !html.includes('__CSS__'), 'no template marker left');
  ok(!/<html|<body|<!doctype/i.test(html), 'a fragment, not a document: the Dashboard wraps it');
  ok(!/\bAdam(?:'s|\s)/.test(html), 'names no person (the repository owner/name aside)');
});

await test('motion plays only for readers who have not asked for less', () => {
  // Every animation and transition in base.css sits inside the one
  // prefers-reduced-motion: no-preference block (found by brace depth).
  const css = fs.readFileSync(path.join(HERE, '..', 'template', 'base.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const open = '@media (prefers-reduced-motion: no-preference) {';
  const at = css.indexOf(open);
  ok(at >= 0, 'base.css has a reduced-motion block');
  let depth = 1, end = at + open.length;
  while (depth && end < css.length) { if (css[end] === '{') depth++; else if (css[end] === '}') depth--; end++; }
  const outside = css.slice(0, at) + css.slice(end);
  eq((outside.match(/(?:^|[;{\s])(?:-webkit-)?(?:animation|transition)(?:-[a-z-]+)?\s*:/g) || []).length, 0, 'animation or transition outside the reduced-motion block');
});
await test('the private page lays out by its own width, not the window', () => {
  // The dashboard pane can be ~400px on a wide window: a window-width rail
  // breakpoint would squeeze the content beside a 212px rail.
  const priv = fs.readFileSync(PRIVATE_PAGE, 'utf8');
  ok(/#ex-root \{[^}]*container-type: inline-size/.test(priv), '#ex-root is a size container');
  eq((priv.match(/@media \((?:max|min)-width/g) || []).length, 0, 'width @media left in the private page');
  ok(/@container \(max-width: 760px\)/.test(priv), 'the narrow layout is a container query');
  const pub = fs.readFileSync(PAGE, 'utf8');
  ok(/@media \(max-width: 760px\)/.test(pub) && !/@container/.test(pub), 'the public page still uses the window width');
});
await test('both pages paint the whole window in the theme color, not only their column', () => {
  // Regression: the dark private page showed a white frame outside the column and below short pages.
  const pub = fs.readFileSync(PAGE, 'utf8'), priv = fs.readFileSync(PRIVATE_PAGE, 'utf8');
  ok(/html \{[^}]*background: var\(--page\)[^}]*min-height: 100%/.test(pub), 'public html background');
  ok(/body \{[^}]*background: var\(--page\)[^}]*min-height: 100vh/.test(pub), 'public body background');
  ok(/html, body \{ background: var\(--color-bg, #E8ECF1\); \}/.test(priv), 'private light background');
  ok(/prefers-color-scheme: dark\) \{ html, body \{ background: var\(--color-bg, #090A10\); \} \}/.test(priv), 'private dark background');
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
  ok(!/<script\b[^>]*\bsrc\s*=/i.test(html) && !/<link\b/i.test(html) && loadsOnlyFonts(html), 'nothing loaded from elsewhere but the font stylesheet');
  const scripts = inlineScripts(html);
  eq(scripts.length, 1, 'one inline script');
  eq(privateLeaks(scripts[0]).join('; '), '');
  ok(!namesRawHost(html), 'the page, noscript text included, names no raw URL');
  ok(html.includes('latest.json') && !html.includes('{{') && !html.includes('__BUNDLE__'), 'the noscript names latest.json; no template marker left');
});

await test('a subject page shows its discarded runs, their cost and top reasons, and nothing when unknown', () => {
  const skill = (d) => doc({ skills: [{ name: 'demo-skill', status: 'covered', verdict: 'keep', runs: [], discarded_runs: d }] });
  const page = (d) => textOf(renderRoute(skill(d), { name: 'skills', id: 'demo-skill' }, {}));
  const text = page({ total: 9, cost_usd: 1.23456, cost_unknown: 1, by_reason: {
    over_cap: { runs: 2, cost_usd: 0.2, cost_unknown: 0 }, fixture_changed: { runs: 5, cost_usd: 1, cost_unknown: 1 },
    unpaired: { runs: 1, cost_usd: 0.03456, cost_unknown: 0 }, duplicate: { runs: 1, cost_usd: 0, cost_unknown: 0 } } });
  ok(text.includes('Discarded runs: 9 runs not counted toward this decision, $1.23 (1 with no recorded cost)'), text);
  ok(text.includes('Most often: fixture changed (5), past the run cap (2), duplicate copy (1)'), text);
  ok(!text.includes('no partner arm'), 'three reasons at most');
  for (const d of [null, { total: 0, cost_usd: 0, cost_unknown: 0, by_reason: {} }]) ok(!page(d).includes('Discarded runs'), JSON.stringify(d));
});

// Run usefulness (Adam, 2026-11-07): rows of `run_utility`, summed over a period
// counted back from the document's generated_at, in UTC days.
const U = (date, cls, runs, cost, reason) => ({ date, model: 'model-a', class: cls, reason: reason || null, runs, cost_usd: cost, cost_unknown: 0 });
const UREF = Date.parse('2026-11-07T20:00:00Z');
const UROWS = [U('2026-11-07', 'decisive', 2, 0.5), U('2026-11-01', 'after_decision', 4, 1), U('2026-10-31', 'stranded', 6, 1.5, 'fixture_changed'),
  U('2026-10-09', 'building', 8, 2), U('2026-10-08', 'discarded', 10, 2.5, 'unpaired'), U(null, 'discarded', 1, 0.25, 'invalid_run'),
  U('2026-11-06', 'decisive_superseded', 3, 0.75, 'subject_changed')];
await test('a period counts back from the reference day, itself included', () => {
  eq(periodStart('7', UREF), '2026-11-01');
  eq(periodStart('30', UREF), '2026-10-09');
  eq(periodStart('all', UREF), null);
  // 2026-11-01 is the 7th day back and in; 2026-10-31 is the 8th and out.
  eq(inPeriod(UROWS, '7', UREF).map((r) => r.date).join(','), '2026-11-07,2026-11-01,2026-11-06');
  // 2026-10-09 is in the last 30 days, 2026-10-08 is not; a row with no day only in all time.
  eq(inPeriod(UROWS, '30', UREF).length, 5);
  eq(inPeriod(UROWS, 'all', UREF).length, 7);
});
await test('the totals split by class, no use is after the decision plus stranded plus discarded', () => {
  eq(NO_USE.join(','), 'after_decision,stranded,discarded');
  const all = utilityTotals(UROWS, 'all', UREF);
  eq(all.total.runs, 34);
  eq(all.noUse.runs, 4 + 6 + 10 + 1);
  eq(all.noUse.cost, 1 + 1.5 + 2.5 + 0.25);
  eq(all.classes.stranded.runs, 6);
  eq(all.classes.decisive_superseded.runs, 3);
  eq(Object.keys(all.reasons).sort().join(','), 'fixture_changed,invalid_run,subject_changed,unpaired');
  const week = utilityTotals(UROWS, '7', UREF);
  eq(week.noUse.runs, 4);
  eq(week.days.map((d) => d.date).join(','), '2026-11-01,2026-11-02,2026-11-03,2026-11-04,2026-11-05,2026-11-06,2026-11-07');
  eq(week.days[1].decisive, undefined, 'an empty day is a gap');
});
await test('a subject page shows run usefulness for the last 30 days, stranded on its own line, and decisions over time', () => {
  const d = doc({ generated_at: '2026-11-07T20:00:00Z', skills: [{ name: 'demo-skill', status: 'covered', verdict: 'keep', runs: [], run_utility: UROWS,
    decisions: [{ fixture: 'task-a', model: 'claude-sonnet-4-5', current: false, from: '2026-10-28', to: '2026-11-02', class: 'benefit', decided: '2026-11-02', pair: null },
      { fixture: 'task-a', model: 'claude-sonnet-4-5', current: true, from: '2026-11-05', to: '2026-11-07', class: 'insufficient', decided: null, pair: null },
      { fixture: 'task-b', model: 'claude-sonnet-4-5', current: false, from: '2026-10-20', to: '2026-10-21', class: 'insufficient', decided: null, pair: null }] }] });
  const node = renderRoute(d, { name: 'skills', id: 'demo-skill' }, {});
  const text = textOf(node);
  ok(text.includes('Run usefulness'), text);
  ok(text.includes('No use: 10 of 23 runs, $2.50 of $5.75.'), text);
  ok(text.includes('Stranded') && text.includes('fixture changed 6 ($1.50)'), text);
  ok(text.includes('v1 kept (helps) on 2026-11-02, runs 2026-10-28 to 2026-11-02; v2 (current) building, runs 2026-11-05 to 2026-11-07'), text);
  ok(text.includes('on task-b: v1 never decided before it changed (stranded), runs 2026-10-20 to 2026-10-21'), text);
  const pressed = findAll(node, (n) => n.tag === 'button' && n.attrs['data-period'] && n.attrs['aria-pressed'] === 'true');
  eq(pressed.map((n) => n.attrs['data-period']).join(','), '30');
  ok(findAll(node, (n) => n.tag === 'rect' && n.attrs['data-class'] === 'stranded').length === 1, 'stranded has its own segment');
  const none = textOf(renderRoute(doc({ skills: [{ name: 'demo-skill', status: 'covered', verdict: 'keep', runs: [], run_utility: null }] }), { name: 'skills', id: 'demo-skill' }, {}));
  ok(!none.includes('Run usefulness'), 'nothing when unknown');
});
await test('the summary shows run usefulness for every subject, skills and guidance', () => {
  const d = doc({ generated_at: '2026-11-07T20:00:00Z', skills: [{ name: 'a', run_utility: [U('2026-11-07', 'decisive', 2, 0.5)] }],
    guidance: { sections: [{ id: 's', run_utility: [U('2026-11-07', 'stranded', 4, 1, 'rest_changed')] }] } });
  const text = textOf(renderRoute(d, { name: 'summary' }, {}));
  ok(text.includes('Run usefulness, every subject'), text);
  ok(text.includes('No use: 4 of 6 runs, $1.00 of $1.50.'), text);
  ok(text.includes('All subjects') && text.includes('Skills') && text.includes('Guidance'), text);
  ok(!textOf(renderRoute(doc({}), { name: 'summary' }, {})).includes('Run usefulness'), 'nothing without a ledger');
});

// Building into decisive (2026-11-08): building runs against decisive ones.
const CDOC = () => doc({ generated_at: '2026-11-08T20:00:00Z',
  skills: [
    { name: 'a', status: 'covered', confidence: { helps: 0.7, no_help: 0.1 }, run_utility: [U('2026-11-05', 'decisive', 10, 1), U('2026-11-05', 'building', 20, 2), U('2026-11-08', 'building', 5, 0.5)],
      decisions: [{ decided: '2026-11-05' }, { decided: '2026-11-05' }, { decided: null }] },
    { name: 'b', status: 'covered', confidence: { helps: 0.4, no_help: 0.2 }, run_utility: [U('2026-11-06', 'decisive_superseded', 4, 0.4), U('2026-11-06', 'stranded', 6, 0.6),
      U('2026-11-08', 'building', 10, 1), U('2026-11-06', 'discarded', 99, 9), U('2026-11-07', 'after_decision', 2, 0.2)], decisions: [{ decided: '2026-11-07' }] },
    { name: 'c', status: 'covered', run_utility: [U('2026-11-07', 'building', 3, 0.3), U('2026-11-07', 'decisive', 1, 0.1)] }],
  guidance: { sections: [{ id: 'g', status: 'skipped', confidence: { helps: 0.9, no_help: 0 }, run_utility: [U('2026-11-07', 'building', 8, 0.8), U('2026-11-08', 'stranded', 2, 0.2)] }] } });
const near = (a, b) => Math.abs(a - b) < 1e-9;
await test('conversion totals sum decided, building and stranded, group building runs by distance, and ignore discarded rows', () => {
  const t = conversionTotals(CDOC());
  eq(t.decided.runs, 15); ok(near(t.decided.cost, 1.5), String(t.decided.cost));
  eq(t.building.runs, 46); ok(near(t.building.cost, 4.6), String(t.building.cost));
  eq(t.stranded.runs, 8); eq(t.after.runs, 2);
  eq(t.resolved.runs, 23);
  ok(near(t.conversion, 15 / 23) && near(t.strandedPerDecided, 8 / 15), 'ratios');
  eq(['near', 'partway', 'far', 'never'].map((g) => t.groups[g].runs).join(','), '25,10,3,8');
  eq(['near', 'partway', 'far', 'never'].map((g) => t.groups[g].subjects).join(','), '1,1,1,1');
  ok(near(t.groups.near.expected, 17.5) && near(t.groups.partway.expected, 3) && near(t.groups.far.expected, 0.3) && t.groups.never.expected === 0, 'expected');
  eq(t.groupsTotal.runs, 46); eq(t.groupsTotal.subjects, 4); ok(near(t.groupsTotal.expected, 20.8), String(t.groupsTotal.expected));
  eq(t.days.map((d) => d.date + ':' + d.decided + '/' + d.building + '/' + d.stranded + '/' + d.after).join(' '), '2026-11-05:10/20/0/0 2026-11-06:4/0/6/0 2026-11-07:1/11/0/2 2026-11-08:0/15/2/0');
  eq(JSON.stringify(t.decisionsByDay), JSON.stringify([{ date: '2026-11-05', cells: 2 }, { date: '2026-11-07', cells: 1 }]));
  eq(['near', 'partway', 'far', 'never', 'total'].map((g) => t.planner.before[g]).join(','), '30,12,4,8,54');
  eq(['near', 'partway', 'far', 'never', 'total'].map((g) => t.planner.since[g]).join(','), '5,10,0,2,17');
  const empty = conversionTotals(doc({ skills: [{ name: 'x', run_utility: [U('2026-11-05', 'building', 3, 1)] }] }));
  eq(empty.conversion, null); eq(empty.strandedPerDecided, null);
});
await test('the summary shows building into decisive with its lead, table, planner link and stranded segments', () => {
  const node = renderRoute(CDOC(), { name: 'summary' }, { ext: makeExt(fakeDash({})) });
  ok(!textOf(renderRoute(CDOC(), { name: 'summary' }, {})).includes('Building into decisive'), 'public render has no panel');
  const text = textOf(node);
  ok(text.includes('Building into decisive'), text);
  ok(text.includes('Of 23 runs that have resolved, 15 helped decide keep or remove (65%) and 8 were stranded by a change first: 0.5 stranded for every one that decided. 46 runs ($4.60) are still building.'), text);
  for (const l of ['Near a verdict (confidence 65% or more)', 'Partway (30% to 65%)', 'Far (under 30%)', 'Never (subject no longer tested)', 'Total']) ok(text.includes(l), l);
  ok(text.includes('~18') && text.includes('~21'), 'expected counts');
  ok(text.includes('Cells that reached a verdict, by day: 11-05 2, 11-07 1.'), text);
  ok(text.includes('Since the deep-before-wide planner change (') && text.includes(', Nov 8 UTC): 17 runs, 29% near a verdict, 59% partway, 0% far, 12% never.') && text.includes('Before it: 54 runs, 56% near a verdict, 22% partway, 7% far, 15% never.'), text);
  const a = findAll(node, (n) => n.tag === 'a' && n.attrs.href === PLANNER_CHANGE.url);
  eq(a.length, 1);
  ok(findAll(node, (n) => n.tag === 'rect' && n.attrs['data-group'] === 'stranded').length === 2, 'stranded segments');
});
await test('building into decisive toggles between percent and run counts', () => {
  const node = renderRoute(CDOC(), { name: 'summary' }, { ext: makeExt(fakeDash({})) });
  const btns = findAll(node, (n) => n.tag === 'button' && n.attrs['data-mode']);
  eq(btns.map((b) => b.attrs['data-mode'] + ':' + b.attrs['aria-pressed']).join(','), 'share:true,count:false');
  const share = textOf(conversionBody(CDOC(), 'share'));
  ok(share.includes('17 runs, 29% near a verdict, 59% partway'), share);
  const count = textOf(conversionBody(CDOC(), 'count'));
  ok(count.includes(', Nov 8 UTC): 17 runs: 5 near a verdict, 10 partway, 0 far, 2 never.'), count);
  ok(count.includes('Before it: 54 runs: 30 near a verdict, 12 partway, 4 far, 8 never.'), count);
  ok(count.includes('Runs by the day they ran, and where they stand now.') && !count.includes('fills from decided'), count);
  // The busiest day (2026-11-05) has 30 runs, so the axis tops out there.
  const top = findAll(conversionBody(CDOC(), 'count'), (n) => n.tag === 'text' && n.children[0] === '30');
  eq(top.length, 1);
  ok(findAll(conversionBody(CDOC(), 'count'), (n) => n.attrs && typeof n.attrs['data-tip'] === 'string' && n.attrs['data-tip'].includes('decided 10, building 20')).length === 1, 'count tooltip');
  ok(findAll(conversionBody(CDOC(), 'share'), (n) => n.tag === 'text' && n.children[0] === '100%').length === 1, 'share axis');
});
await test('no building into decisive panel when no subject has run_utility', () => {
  ok(conversionView(doc({ skills: [{ name: 'a' }] })) === null, 'null view');
  ok(!textOf(renderRoute(doc({ skills: [{ name: 'a' }] }), { name: 'summary' }, { ext: makeExt(fakeDash({})) })).includes('Building into decisive'), 'no heading');
});

await test('the judge cell says why a judge was skipped, with both check counts', () => {
  const run = (o) => ({ skill: 'example-skill', with_skill: 4, without_skill: 1, checks: 4, with_judge: null, without_judge: null, ...o });
  eq(judgeCell(run({})), 'skipped: the version with the skill passed more checks (4 of 4 vs 1 of 4)');
  eq(judgeCell(run({ skill: 'guidance/example-section', with_skill: 3, without_skill: 1 })), 'skipped: the full-guidance version passed more checks (3 of 4 vs 1 of 4)');
  eq(judgeCell(run({ with_skill: 7.333333333333333, without_skill: 5, checks: 12 })), 'skipped: the version with the skill passed more checks (7.3 of 12 vs 5 of 12)');
  eq(judgeCell(run({ checks: null })), 'skipped');
  // The row's judge field decides what may be claimed.
  eq(judgeCell(run({ judge: 'skipped: checks decided' })), 'skipped: the version with the skill passed more checks (4 of 4 vs 1 of 4)');
  eq(judgeCell(run({ judge: 'skipped: checks decided', skill: 'guidance/example-section' })), 'skipped: the full-guidance version passed more checks (4 of 4 vs 1 of 4)');
  eq(judgeCell(run({ judge: 'skipped: checks decided', with_skill: 2, without_skill: 2 })), 'skipped');
  eq(judgeCell(run({ judge: 'not run' })), 'not run');
  eq(judgeCell(run({ judge: 'not run', with_skill: 1, without_skill: 4 })), 'not run');
  eq(judgeCell(run({ judge: 'ran', with_judge: 7, without_judge: 8 })), '7.0 vs 8.0');
  eq(judgeCell(run({ with_skill: 4, without_skill: 4 })), 'not recorded');
  eq(judgeCell(run({ with_skill: 3, without_skill: 4 })), 'not recorded');
  eq(judgeCell(run({ with_judge: 7.25, without_judge: 9 })), '7.3 vs 9.0');
  eq(judgeCell(run({ with_judge: 6, without_judge: 6, with_skill: 4, without_skill: 4 })), '6.0 vs 6.0');
});

for (const f of failures) console.log('FAIL ' + f);
console.log(passed + ' passed, ' + failures.length + ' failed');
process.exit(failures.length ? 1 : 0);
