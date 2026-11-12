// Tests for explorer/: the dashboard adapter, the public bundle's contents and
// the build's output. Plain Node plus the pinned devDependencies, no network.
// Run: npm test   (in explorer/; exits nonzero on any failure)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as acorn from 'acorn';
import vm from 'node:vm';
import { bundle, bundleResult, buildPublicPage, buildPrivatePage, buildArtifactPage } from '../build.js';
import { readDashboard, dashboardSource, DATASET_ID } from '../src/adapters/dashboard.js';
import { DEFAULT_DATA_URL, DATA_URL_PREFIX, allowedDataUrl } from '../src/adapters/web.js';
import * as artifactAdapter from '../src/adapters/artifact.js';
import * as webAdapter from '../src/adapters/web.js';
import { DATA_REPO } from '../src/config.js';
import { SCHEMA_VERSION } from '../src/core/rules.js';
import { fixtureQueue, requestIssue } from '../src/core/fixtures.js';
import { privateSource, PRIVATE_DATASET_ID, GROUPS } from '../src/entries/private.js';
import { makeExt, attentionRows, attentionGroups, capUse, routineHealth, snapshotMs, staleHours } from '../src/private/views.js';
import { mergePrivate } from '../src/private/merge.js';
import { rowsOf, some } from '../src/private/datasets.js';
import { judgeCell } from '../src/views/subject.js';
import { renderRoute } from '../src/views/page.js';
import { agentMadeRows, spendWeeks } from '../src/views/impact.js';
import { conversionTotals, conversionView, conversionBody, PLANNER_CHANGE } from '../src/private/conversion.js';
import { utilityTotals, periodStart, inPeriod, NO_USE, noUseShare } from '../src/views/utility.js';
import { textOf, findAll, h, toDom, SVG_TAGS } from '../src/core/h.js';
// The href attribute values read off the rendered links, as a set: a link is matched by exact equality, never as a substring.
const hrefSet = (hrefs) => new Set(hrefs);
import { hashFor, parseRoute, GROUPS as ROUTE_GROUPS } from '../src/core/route.js';
import { sectionItems, skillItems } from '../src/core/items.js';
import { trendingRows } from '../src/views/trending.js';
import { changeRows, pullKind, pullSubject } from '../src/views/changes.js';
import { LOOP_KINDS, LOOP_TITLE, LOOP_BRANCH, isLoopPull } from '../src/views/loop.js';
import { fmtUsd } from '../src/core/format.js';
import { weekChart } from '../src/views/weekchart.js';
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

await test('every SVG element name the page draws is in SVG_TAGS, so it gets the SVG namespace', () => {
  const known = ['svg', 'g', 'path', 'rect', 'line', 'polyline', 'polygon', 'circle', 'ellipse', 'text', 'tspan', 'title', 'defs', 'use', 'clipPath', 'linearGradient', 'stop', 'marker'];
  const used = new Set();
  const walkDir = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
    const f = path.join(d, e.name);
    if (e.isDirectory()) return walkDir(f);
    if (!f.endsWith('.js')) return;
    (function walk(n) {
      if (!n || typeof n.type !== 'string') return;
      if (n.type === 'CallExpression' && n.callee.type === 'Identifier' && n.callee.name === 'h' && n.arguments[0] && n.arguments[0].type === 'Literal') used.add(n.arguments[0].value);
      for (const [k, v] of Object.entries(n)) { if (k === 'type') continue; if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v); }
    })(acorn.parse(fs.readFileSync(f, 'utf8'), { ecmaVersion: 'latest', sourceType: 'module' }));
  });
  walkDir(path.join(EXPLORER, 'src'));
  const svg = known.filter((t) => used.has(t));
  ok(svg.includes('polygon') && svg.includes('rect'), 'the scan finds the drawn tags: ' + svg);
  const missing = svg.filter((t) => !SVG_TAGS.has(t));
  eq(missing.join(','), '', 'drawn SVG tags missing from SVG_TAGS');
});
await test('the weekly chart break mark becomes an SVG-namespace element', () => {
  const made = [];
  const doc = { createTextNode: (t) => ({ text: t }), createElement: (t) => ({ ns: null, t, setAttribute() {}, addEventListener() {}, appendChild() {} }),
    createElementNS: (ns, t) => { const e = { ns, t, setAttribute() {}, addEventListener() {}, appendChild() {} }; made.push(e); return e; } };
  const wk = (a, b) => ({ label: 'w', a, b });
  toDom(weekChart([wk(0, 0), wk(498, 0), wk(1, 11), wk(0, 3)], ['Local blocks', 'CI blocks'], 'a', 't', []), doc);
  const poly = made.filter((e) => e.t === 'polygon');
  eq(poly.length, 1, 'one break mark');
  eq(poly[0].ns, 'http://www.w3.org/2000/svg');
});
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
  const dash = fakeDash({ waiting: okData([{ id: 'none', item: 'Nothing' }]), checkins: okData([{ id: 'none' }, { id: 'k', when: '2026-10-26' }]),
    routines: { status: 'loading' } });
  eq(rowsOf(dash, 'waiting').length, 0);
  eq(some(dash, 'waiting'), null);
  eq(rowsOf(dash, 'checkins').length, 1);
  eq(rowsOf(dash, 'routines'), null, 'loading');
  eq(rowsOf(dash, 'no_such'), null, 'missing');
  const ext = makeExt(dash);
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
  const t = textOf(renderRoute(d, { name: 'changes', id: null }, { ext: makeExt(fakeDash({})) }));
  ok(!textOf(renderRoute(d, { name: 'needs', id: null }, { ext: makeExt(fakeDash({})) })).includes(STRINGS.trendingHeading), 'Needs you no longer repeats it');
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
  eq(textOf(findAll(alertTile, (n) => n.attrs && /tile-num/.test(n.attrs.class || ''))[0]).trim().split(' ').pop(), String(attentionRows(fakeDash({}), d).length), 'the tile counts the rows Needs you lists');
  eq(findAll(alertTile, (n) => n.tag === 'a')[0].attrs.href, hashFor('needs'), 'it opens Needs you');
});
await test('the allowance and routine health come from their datasets', () => {
  const cap = capUse([{ points: 40.5, account_week_used: 70, pace_room_points: 3, account_reading_at: '2026-11-04T03:30:10Z', week_resets_at: '2026-11-09T17:00:00Z' }],
    [{ setting: 'weekly_cap', value: 1 }, { setting: 'stop_when_account_above', value: 0.9 }, { setting: 'per_run_cap', value: 0.01 }, { setting: 'per_run_overrun', value: 0.002 }]);
  eq(cap.spent, 40.5); eq(cap.cap, 100); eq(cap.stop, 90); eq(cap.room, 59.5);
  eq(Math.round(cap.reservation * 1000) / 1000, 1.2);
  eq(capUse(null, []), null);
  const rh = routineHealth([{ health: 'OK' }, { health: 'Stalled' }, { health: 'Not run yet' }]);
  eq(JSON.stringify(rh), '{"active":3,"ok":1,"fresh":1,"attention":1}');
  // Every shape of mix: healthy, not run yet and needing a look always add up to the rows the table lists.
  for (const mix of [[], ['OK'], ['Not run yet'], ['OK', 'Late', 'Not run yet', 'Failing', 'Paused', 'Check', 'Not run yet']]) {
    const r = routineHealth(mix.map((health) => ({ health })));
    eq(r.ok + r.fresh + r.attention, r.active, mix.join(','));
    eq(r.active, mix.length);
  }
});
await test('the private build has six groups, Needs you second, and speaks to "you"', () => {
  eq(GROUPS.join(','), 'summary,needs,changes,results,spend,activity');
  const dash = fakeDash({ waiting: okData([{ id: 'w1', item: 'Approve the example hook', where: 'example-owner/r', link: 'https://github.com/example-owner/r/pull/3', since: '2026-10-30T00:00:00Z' }]) });
  useVoice('you');
  try {
    const node = renderRoute(doc(), { name: 'needs', id: null }, { ext: makeExt(dash) });
    const t = textOf(node);
    ok(t.includes('Approve the example hook') && t.includes(STRINGS.groups.needs), t);
    ok(!/the owner/.test(t), 'no third person in the private voice');
    const hrefs = findAll(node, (n) => n.tag === 'a').map((n) => n.attrs.href);
    ok(hrefSet(hrefs).has('https://github.com/example-owner/r/pull/3'), 'the waiting item links to its page');
    ok(hrefs.every((u) => /^(https:\/\/github\.com\/|#\/[a-z]+$)/.test(u)), 'only GitHub and this page: ' + hrefs.join(' '));
  } finally { useVoice('owner'); }
  const pub = textOf(renderRoute(doc(), { name: 'needs', id: null }, {}));
  ok(!pub.includes('Approve the example hook'), 'no Needs you content without the private overlays');
});
await test('every route renders with the private overlays and every dataset empty or loading', () => {
  const ext = makeExt(fakeDash({}));
  for (const name of ['summary', 'needs', 'hooks', 'skills', 'guidance', 'method', 'changes', 'spend', 'activity']) {
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
  ok(!textOf(renderRoute(doc(), { name: 'spend', id: null }, {})).includes(STRINGS.agentMade), 'no panel without the block');
});
await test('made by agents: counts by kind, agent items newest first, linked to their pages', () => {
  const r = agentMadeRows(amDoc());
  eq(r.kinds.map((k) => [k.kind, k.total, k.agent, k.afterRule].join(':')).join(','), 'check:1:1:1,skill:1:1:0,section:1:0:0');
  eq(r.kinds[0].impact, '12 runs, 3 blocked; verdicts: blocks 1');
  eq(r.items.map((i) => i.id).join(','), 'demo-check,demo-skill');
  const node = renderRoute(amDoc(), { name: 'spend', id: null }, {});
  ok(textOf(node).includes(STRINGS.agentMade), 'panel shown');
  const hrefs = findAll(node, (n) => n.tag === 'a').map((n) => n.attrs.href);
  ok(hrefSet(hrefs).has('#/hooks/demo-check') && hrefSet(hrefs).has('#/skills/demo-skill'), hrefs.join(' '));
  ok(!hrefSet(hrefs).has('#/guidance/demo-section'), 'person-made items are counted, not listed');
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

// --- review 2026-11-12, batch A: each fix is tested through the public entry points ----------
await test('C1: fixtures join their request whether it is a number or an issue URL, and the rows add up to the totals', () => {
  const url = (n) => 'https://github.com/' + DATA_REPO + '/issues/' + n;
  const q = fixtureQueue(fqDoc({ fixtures: [
    { path: 'a', subject: 's', origin_kind: 'real-work', request: url(12), runs: 4, cost_usd: 1.25 },
    { path: 'b', subject: 's', origin_kind: 'invented', request: 12, runs: 2, cost_usd: 0.5 },
    { path: 'c', subject: 'o', origin_kind: 'invented', request: url(99), runs: 7, cost_usd: 9 },
    { path: 'd', subject: 'o', origin_kind: 'invented', request: null, runs: 1, cost_usd: 0 },
    { path: 'e', subject: 'o', origin_kind: 'invented', request: 'https://github.com/other-owner/other-repo/issues/12', runs: 1, cost_usd: 0 },
    { path: 'f', subject: 'o', origin_kind: 'invented', request: '12', runs: 1, cost_usd: 0 }] }), FQ_REF);
  eq(q.rows.find((r) => r.issue === 12).fixtures, 3, 'a URL, a numeric and a bare-digit request all reach issue 12');
  eq(q.unlisted.fixtures, 1, 'the fixtures of requests not listed');
  eq(q.noRequest.fixtures, 2, 'no request, or a request in another repository, names no issue here');
  eq(requestIssue('https://github.com/other-owner/other-repo/issues/12'), null);
  eq(requestIssue('12abc'), null); eq(requestIssue(undefined), null); eq(requestIssue(0), null);
  eq(q.rows.reduce((t, r) => t + r.fixtures, 0) + q.unlisted.fixtures + q.noRequest.fixtures, 6, 'rows add up to every fixture');
  eq(q.rows.reduce((t, r) => t + r.runs, 0) + q.unlisted.runs + q.noRequest.runs, 16);
  const text = textOf(renderRoute(doc({ fixture_queue: fqDoc({ fixtures: [{ path: 'c', origin_kind: 'invented', request: url(99), runs: 7, cost_usd: 9 }] }).fixture_queue }), { name: 'changes', id: null }, {}));
  ok(text.includes(STRINGS.fqUnlisted), 'the page shows the unlisted row');
  const node = renderRoute(doc({ fixture_queue: fqDoc({ fixtures: [{ path: 'c', origin_kind: 'invented', request: url(99), runs: 7, cost_usd: 9 }, { path: 'n', origin_kind: 'invented', runs: 1 }] }).fixture_queue }), { name: 'changes', id: null }, {});
  const foot = findAll(node, (n) => n.tag === 'tfoot');
  eq(foot.length, 1, 'the summary rows sit in a tfoot, so sorting cannot move them');
  ok(textOf(foot[0]).includes(STRINGS.fqUnlisted) && textOf(foot[0]).includes(STRINGS.fqNoRequest), textOf(foot[0]));
});
const PULL = (n, title, head, extra) => Object.assign({ repo: 'Adam-S-Daniel/adam-agentskills', number: n, title, head_ref: head, state: 'merged',
  created_at: '2026-11-07T10:00:00Z', updated_at: '2026-11-07T11:00:00Z', merged_at: '2026-11-07T11:00:00Z', url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pull/' + n }, extra || {});
await test('C2: loop pull requests are selected by head-branch prefix, with the title rule for data older than head_ref', () => {
  const forms = [
    [PULL(1, 'Proposed workflow-path-audit SKILL.md edit (improvement run r1)', 'eval-improve/workflow-path-audit'), 'improve skill'],
    [PULL(2, 'Proposed some-section guidance edit (improvement run r2)', 'eval-guidance-improve/some-section'), 'improve guidance'],
    [PULL(3, 'Add a skill', 'draft-skill/new-thing'), 'draft by branch'],
    [PULL(4, 'Whatever the gate says', 'retire-skill/old-thing'), 'retire skill by branch'],
    [PULL(5, 'Whatever the gate says', 'retire-guidance/old-section'), 'retire guidance by branch'],
    [PULL(6, 'Proposed older-skill SKILL.md edit (improvement run r6)', null), 'title only, old data'],
    [PULL(7, 'Retire skill x: no benefit on every roster model (#70)', null), 'retire title only'],
    [PULL(8, 'Fix a typo', 'fix/typo'), 'not the loop'],
    [PULL(9, 'Improve the docs', 'claude/x'), 'a loop-looking title on a non-loop branch'],
    [PULL(10, 'Remove some-plugin/some-skill: unused (skills-evals removal policy)', null), 'unused removal title only']];
  const rows = changeRows(doc({ generated_at: '2026-11-12T17:00:00Z', activity: { fetched_at: '2026-11-12T17:00:00Z', since: '2026-10-29T17:00:00Z', repos: [], issues: [], runs: [], pulls: forms.map((f) => f[0]) } }));
  const listed = rows.map((r) => r.pr && r.pr.number);
  for (const [p, what] of forms.filter((f) => ![8, 9].includes(f[0].number))) ok(listed.includes(p.number), what + ' is listed');
  ok(!listed.includes(8), 'an ordinary pull request is not');
  ok(!listed.includes(9), 'a known non-loop branch decides, whatever the title says');
});
const ALLOW = (over) => okData([Object.assign({ measure: 'eval_spend_since_reset', points: 54.4, pace_room_points: 14.1, account_week_used: 40, account_reading_at: '2026-11-12T17:00:00Z', week_resets_at: '2026-11-16T17:00:00Z' }, over || {})]);
const BUDGET = okData([{ setting: 'weekly_cap', value: 0.25 }, { setting: 'stop_when_account_above', value: 0.9 }, { setting: 'per_run_cap', value: 0.01 }, { setting: 'per_run_overrun', value: 0.002 }]);
const P_PACE = 'Use is above the weekly cap, but the guard still reports room';
const needs = (allow) => renderRoute(doc(), { name: 'needs', id: null }, { ext: makeExt(fakeDash({ eval_allowance: allow, budget: BUDGET })) });
await test('C3: the allowance label names its basis and reset, and a bar over the cap is not red while there is room', () => {
  const full = (n) => findAll(n, (x) => x.tag === 'div' && String(x.attrs && x.attrs.class || '').split(' ').includes('over')).length;
  const rolling = needs(ALLOW({ measure: 'eval_spend_7d' }));
  ok(textOf(rolling).includes('Test use, last 7 days: 54.4 points (weekly cap 25)'), textOf(rolling));
  eq(full(rolling), 0, 'room above 0, so no red bar');
  const reset = textOf(needs(ALLOW({ points: 7 }))).replace(/\s+/g, ' ');
  ok(reset.includes('Test use since the Monday noon ET reset: 7.0 of 25 points'), reset);
  const midweek = textOf(needs(ALLOW({ points: 7, window_start: '2026-11-11T19:15:00Z' }))).replace(/\s+/g, ' ');
  ok(midweek.includes('Test use since the Wednesday 2:15 PM ET reset: 7.0 of 25 points'), 'a manual mid-week reset is labeled from window_start: ' + midweek);
  const sinceOver = needs(ALLOW({ points: 54.4, room_points: 3 }));
  ok(textOf(sinceOver).includes(P_PACE), 'the since-reset basis gets the pace note too');
  eq(full(sinceOver), 0);
  const none = needs(ALLOW({ measure: 'eval_spend_7d', points: 90, pace_room_points: 0 }));
  eq(full(none), 1, 'no room and over the cap is red');
});
await test('C3: the guard\'s own room_points is used when present, and rows without it still re-derive room', () => {
  const rows = (extra) => [Object.assign({ points: 54.4, pace_room_points: 14.1, account_reading_at: '2026-11-12T17:00:00Z', week_resets_at: '2026-11-16T17:00:00Z' }, extra)];
  const budget = BUDGET.data;
  eq(capUse(rows({ room_points: 3.5 }), budget).room, 3.5, 'room_points wins');
  eq(capUse(rows({ room_points: 0 }), budget).room, 0, 'zero room is zero, not the pace figure');
  eq(capUse(rows({}), budget).room, 14.1, 'old rows keep the derived room');
  const t = textOf(needs(ALLOW({ room_points: 0, points: 90 }))).replace(/\s+/g, ' ');
  ok(t.includes('Room for new tests now: about 0.0 points'), t);
});
await test('C4: each panel prints its own block time, never one document time, and the page says the range', () => {
  const d = doc({ generated_at: '2026-11-12T16:54:13Z', activity: { fetched_at: '2026-11-12T17:45:57Z', since: '2026-10-29T17:00:00Z', repos: ['Adam-S-Daniel/skills-evals'],
    runs: [{ repo: 'Adam-S-Daniel/skills-evals', run_id: 5, workflow: 'CI', title: 'CI', event: 'push', state: 'completed', conclusion: 'success', created_at: '2026-11-12T17:36:00Z', updated_at: '2026-11-12T17:40:00Z', url: 'https://github.com/Adam-S-Daniel/skills-evals/actions/runs/5' }],
    pulls: [], issues: [] }, fixture_queue: Object.assign({}, fqDoc().fixture_queue, { generated_at: '2026-11-12T17:45:00Z' }) });
  const ops = textOf(renderRoute(d, { name: 'activity', id: null }, {})).replace(/\s+/g, ' ');
  ok(ops.includes('as of Nov 12, 2026, 12:45 PM ET'), ops);
  ok(/Data read between Nov 12, 2026, 11:54 AM ET and Nov 12, 2026, 12:45 PM ET/.test(ops), ops);
  const loop = textOf(renderRoute(d, { name: 'changes', id: null }, {})).replace(/\s+/g, ' ');
  ok(loop.includes('Fixture requests From the results document, as of Nov 12, 2026, 12:45 PM ET'), loop);
});
await test('C4 guard: no view prints the single document time for a panel (srcLine(STRINGS.srcDoc, refMs))', () => {
  const dir = path.join(EXPLORER, 'src', 'views');
  const found = [];
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.js'))) {
    const ast = acorn.parse(fs.readFileSync(path.join(dir, f), 'utf8'), { ecmaVersion: 'latest', sourceType: 'module' });
    (function walk(n) {
      if (!n || typeof n.type !== 'string') return;
      if (n.type === 'CallExpression' && n.callee.type === 'Identifier' && n.callee.name === 'srcLine' && n.arguments.length === 2
        && n.arguments[0].type === 'MemberExpression' && n.arguments[0].object.name === 'STRINGS' && n.arguments[0].property.name === 'srcDoc'
        && n.arguments[1].type === 'Identifier' && n.arguments[1].name === 'refMs') found.push(f);
      for (const [k, v] of Object.entries(n)) { if (k === 'type') continue; if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v); }
    })(ast);
  }
  eq(found.join(','), '', 'use rangeLine(doc) or srcLineFor(doc, block)');
});
await test('money is printed with thousands separators everywhere', () => {
  eq(fmtUsd(5541.65), '$5,541.65'); eq(fmtUsd(0), '$0.00'); eq(fmtUsd(12.5), '$12.50');
  const dir = path.join(EXPLORER, 'src');
  const bad = [];
  (function scan(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { scan(p); continue; }
      if (!p.endsWith('.js')) continue;
      (function walk(n) {
        if (!n || typeof n.type !== 'string') return;
        if (n.type === 'BinaryExpression' && n.operator === '+' && n.left.type === 'Literal' && n.left.value === '$'
          && n.right.type === 'CallExpression' && n.right.callee.property && n.right.callee.property.name === 'toFixed') bad.push(path.relative(dir, p));
        for (const [k, v] of Object.entries(n)) { if (k === 'type') continue; if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v); }
      })(acorn.parse(fs.readFileSync(p, 'utf8'), { ecmaVersion: 'latest', sourceType: 'module' }));
    }
  })(dir);
  eq(bad.join(','), '', 'format dollars with fmtUsd');
});
await test('C5: the weekly dollar columns sum to the total in the one sentence', () => {
  const weeks = [{ week: '2026-11-09', eval_runs: 3, plan_meter_points: 1, api_usd: 14.41, thread_spend_usd: 335.49, run_usd: 91.75, cost_per_verdict: 99 },
    { week: '2026-11-02', eval_runs: 5, plan_meter_points: 2, api_usd: 200, thread_spend_usd: 4000, run_usd: 900, cost_per_verdict: null }];
  const sum = (k) => weeks.reduce((t, w) => t + w[k], 0);
  const total = { since: '2026-10-19', usd: sum('api_usd') + sum('thread_spend_usd') + sum('run_usd'), run_usd: sum('run_usd'), thread_spend_usd: sum('thread_spend_usd'), api_usd: sum('api_usd'), verdicts: 12, cost_per_verdict: 0 };
  total.cost_per_verdict = total.usd / 12;
  const t = textOf(renderRoute(doc({ spend: { generated_at: '2026-11-12T01:00:00Z', weeks, total } }), { name: 'spend', id: null }, {})).replace(/\s+/g, ' ');
  ok(t.includes('Since Oct 19: $5,541.65 for 12 decided verdicts, $461.80 each (tests $991.75, building $4,335.49, API $214.41)'), t);
  ok(t.includes(STRINGS.colRunsUsd), 'a Tests $ column');
  ok(!t.includes('Per verdict $'), 'no per-verdict column in a week row');
  eq(Math.round((sum('run_usd') + sum('thread_spend_usd') + sum('api_usd')) * 100), Math.round(total.usd * 100), 'the three columns add to the total');
  const old = textOf(renderRoute(doc({ spend: { generated_at: '2026-11-12T01:00:00Z', weeks: weeks.map((w) => { const c = Object.assign({}, w); delete c.run_usd; return c; }) } }), { name: 'spend', id: null }, {}));
  ok(old.includes(STRINGS.colRunsUsd), 'data without run_usd or total still renders');
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
// The negative controls below need the private bundle readable (names kept, so
// the leak check can see `dash`), which the shipped private page is not.
const privateJs = await bundle('private.js', { minifySyntax: false, minifyWhitespace: false, minifyIdentifiers: false });
// Which source files went into a bundle, from esbuild's metafile: a fact about
// the build, where a path comment in the output text is only a habit of the printer.
const inputsOf = async (entry) => new Set(Object.keys((await bundleResult(entry, { minifySyntax: true, minifyWhitespace: false, minifyIdentifiers: false })).metafile.inputs));
const PUBLIC_INPUTS = await inputsOf('public.js'), PRIVATE_INPUTS = await inputsOf('private.js'), ARTIFACT_INPUTS = await inputsOf('artifact.js');
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
    ok(PRIVATE_INPUTS.has(m), 'the private bundle includes ' + m);
    ok(!PUBLIC_INPUTS.has(m), 'the public bundle includes ' + m);
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
// The shipped private page is minified (syntax, whitespace and identifiers); every
// other test runs the readable bundle, so run the committed script itself too.
await test('the committed private page script runs and answers like the readable bundle', () => {
  const scripts = inlineScripts(fs.readFileSync(PRIVATE_PAGE, 'utf8'));
  eq(scripts.length, 1, 'one inline script');
  const sandbox = { module: { exports: {} }, URL, URLSearchParams, Intl, console, Date, Math, JSON };
  vm.runInNewContext(scripts[0], sandbox, { filename: 'dashboard-page.js' });
  const shipped = sandbox.module.exports;
  eq(Object.keys(shipped).sort().join(','), Object.keys(exportsOf(privateJs)).sort().join(','), 'the same exports');
  eq(JSON.stringify(shipped.routineHealth([{ health: 'OK' }, { health: 'Late' }, { health: 'Not run yet' }])), '{"active":3,"ok":1,"fresh":1,"attention":1}');
  eq(shipped.staleHours(Date.parse('2026-11-12T01:00:00Z'), Date.parse('2026-11-12T20:00:00Z'), 12), 19);
  eq(shipped.staleHours(Date.parse('2026-11-12T01:00:00Z'), Date.parse('2026-11-12T20:00:00Z'), 24), null);
});
// Headroom: each page must stay at least 8 KB under its cap, so a change that
// eats the margin fails here, before the page can no longer be stored. The
// private cap is the ArtifactData document limit (JSON-serialized); the public
// 256 KB budget is a size choice for a page that is one self-contained file
// people open straight from the repository (tool/test/run.js holds the cap).
await test('both pages keep 8 KB of headroom under their caps', () => {
  const HEADROOM = 8 * 1024;
  const priv = Buffer.byteLength(JSON.stringify({ text: fs.readFileSync(PRIVATE_PAGE, 'utf8') }), 'utf8');
  const pub = fs.statSync(PAGE).size;
  ok(priv <= 262144 - HEADROOM, 'private page serialized is ' + priv + ' bytes, within 8 KB of 262,144');
  ok(pub <= 256 * 1024 - HEADROOM, 'public page is ' + pub + ' bytes, within 8 KB of 256 KB');
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
  ok(!ARTIFACT_INPUTS.has('src/adapters/web.js') && ARTIFACT_INPUTS.has('src/adapters/artifact.js'), 'web.js is replaced by artifact.js');
  ok(PUBLIC_INPUTS.has('src/adapters/web.js') && !PUBLIC_INPUTS.has('src/adapters/artifact.js'), 'the public bundle keeps web.js');
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
    ok(PRIVATE_INPUTS.has(m) && !ARTIFACT_INPUTS.has(m), 'the artifact bundle includes ' + m);
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


// --- review 2026-11-12, batch C: Needs you, changes, spend, data age, groups ---------------
const NOW_ET4PM = Date.parse('2026-11-12T21:00:00Z');
const SNAP_OK = () => okData([{ measure: 'eval_spend_since_reset', points: 10, pace_room_points: 5, room_points: 5, account_reading_at: '2026-11-12T12:00:00Z',
  week_resets_at: '2026-11-16T17:00:00Z', computed_at: '2026-11-12T20:00:00Z' }]);
const routine = (name, health) => ({ name, health, last_run: '2026-11-12T10:00:00Z', link: null });
const needsDash = (extra) => fakeDash(Object.assign({ eval_allowance: SNAP_OK(), budget: BUDGET, waiting: okData([{ id: 'none', item: 'Nothing waiting on you' }]),
  routines: okData([routine('R1', 'OK'), routine('R2', 'OK')]),
  half_built_summary: okData([{ open: 0, high: 0, broken: 0, needs_owner: 0, fixed_7d: 2, checked_at: '2026-11-12T10:00:00Z' }]) }, extra || {}));
const needsPage = (dash, d) => renderRoute(d || doc({ newest_run: '2026-11-12T15:00:00Z', generated_at: '2026-11-12T19:00:00Z' }), { name: 'needs', id: null }, { ext: makeExt(dash, { now: () => NOW_ET4PM }) });
const flat = (node) => textOf(node).replace(/\s+/g, ' ');

await test('R3 recommendation 3: with nothing waiting and every routine on time, Needs you says so, in order, and folds the healthy routines', () => {
  const node = needsPage(needsDash());
  const t = flat(node);
  ok(t.includes('Nothing is waiting on you.'), t);
  ok(t.includes('Loop healthy: last test Nov 12, 2026, 10:00 AM ET'), t);
  ok(t.includes('2 of 2 routines on time') && t.includes('data read Nov 12, 2026, 2:00 PM ET'), t);
  ok(t.includes('Show 2 healthy routines'), 'the healthy routines fold');
  ok(!t.includes(STRINGS.trendingHeading) && !t.includes('Half-built and broken features'), 'no trending table, and no half-built banner at zero');
  const at = (x) => t.indexOf(x);
  ok(at('Waiting on you') < at('Loop health') && at('Loop health') < at('Needs attention') && at('Needs attention') < at("This week's test allowance") && at("This week's test allowance") < at('Routine health'), 'the order');
  const hrefs = findAll(node, (n) => n.tag === 'a').map((n) => n.attrs.href);
  for (const h of ['#/activity', '#/changes', '#/spend', '#/summary']) ok(hrefSet(hrefs).has(h), 'the strip links ' + h);
  const folded = findAll(node, (n) => n.tag === 'details' && textOf(n).includes('R1'));
  eq(folded.length, 1, 'both healthy routines sit under one fold');
});
await test('R3 recommendation 3: a late routine reads as a problem outside the fold, and a waiting item shows why', () => {
  const dash = needsDash({ routines: okData([routine('Good', 'OK'), routine('Bad', 'Late')]),
    waiting: okData([{ id: 'w', item: 'Review the thing', why: 'Ready for your review', where: 'Thread', link: 'https://claude.ai/code/x', since: '2026-11-12T12:00:00Z' }]),
    half_built_summary: okData([{ open: 3, high: 1, broken: 0, needs_owner: 1, fixed_7d: 0, checked_at: '2026-11-12T10:00:00Z' }]) });
  const node = needsPage(dash);
  const t = flat(node);
  ok(t.includes('Loop needs a look: last test') && t.includes('1 of 2 routines late, failing or to check'), t);
  ok(t.includes('Ready for your review') && t.includes('Review the thing') && !t.includes('Nothing is waiting on you.'), t);
  ok(t.includes('Half-built and broken features'), 'the banner shows when its count is above 0');
  ok(findAll(node, (n) => n.tag === 'details').every((d) => !textOf(d).includes('Bad')), 'a problem is never inside a fold');
  ok(t.includes('Show 1 healthy routine') && !t.includes('Show 1 healthy routines'), 'singular');
  const unknown = flat(needsPage(needsDash({ routines: { status: 'loading' } })));
  ok(unknown.includes('Loop health unknown:') && !unknown.includes('Loop healthy'), 'no routine data is not a healthy loop');
});
await test('R3 recommendation 3: an empty address opens Needs you in the private build only', () => {
  const priv = GROUPS, pub = ['summary', 'changes', 'results', 'spend', 'activity'];
  eq(parseRoute('', '', priv, 'needs').name, 'needs');
  eq(parseRoute('', '', pub, 'needs').name, 'summary');
  eq(parseRoute('#/summary', '', priv, 'needs').name, 'summary', 'a link to Summary still opens it');
  const src = fs.readFileSync(path.join(EXPLORER, 'src', 'entries', 'private.js'), 'utf8');
  ok(/home:\s*'needs'/.test(src), 'the private entry boots with home: needs');
});
const DRIFT = (n) => ({ kind: 'context-drift', subject: 'skill', name: 'skill-' + (n % 14), fixture: 'fx-' + n, repository: 'example-owner/r', drift_since: n === 0 ? '2026-11-02T10:00:00Z' : '2026-11-05T10:00:00Z' });
await test('R3 recommendation 4: 29 context-drift rows are one row that says who acts, with all 29 under a fold', () => {
  const alerts = Array.from({ length: 29 }, (_, i) => DRIFT(i));
  const dash = needsDash({ half_built_issues: okData([{ key: 'k1', state: 'open', kind: 'partial', severity: 'low', title: 'One', url: null }]) });
  const d = doc({ alerts, generated_at: '2026-11-12T19:00:00Z' });
  const flatRows = attentionRows(dash, d);
  eq(flatRows.length, 30, 'attentionRows stays the flat list the Summary count reads');
  const groups = attentionGroups(flatRows);
  ok(groups.length <= 5 && groups.length === 2, 'at most 5 rows: ' + groups.length);
  const g = groups.find((r) => r.children);
  eq(g.children.length, 29);
  eq(g.what, 'Re-pin 29 tests across 14 skills');
  ok(/Nothing re-pins them on its own/.test(g.note) && g.note.includes('Nov 2'), g.note);
  const node = needsPage(dash, d);
  const fold = findAll(node, (n) => n.tag === 'details' && textOf(n).includes('Show all 29'))[0];
  ok(fold, 'a fold labeled with the count');
  eq(findAll(fold, (n) => n.tag === 'li').length, 29, 'expanding shows all 29');
  // Three or fewer rows of a kind stay separate rows.
  eq(attentionGroups(attentionRows(fakeDash({}), doc({ alerts: alerts.slice(0, 3) }))).length, 3);
  eq(attentionGroups(attentionRows(fakeDash({}), doc({ alerts: alerts.slice(0, 4) }))).length, 1);
});
await test('PR 984: the refresh clock, not the allowance row, decides the banner', () => {
  const ALLOW = okData([{ measure: 'eval_spend_since_reset', points: 1, pace_room_points: 1, computed_at: '2026-11-12T00:00:00Z' }]);
  const refresh = (iso, every) => okData([{ refreshed_at: iso, refresh_every_hours: every }]);
  const banner = (dash) => flat(renderRoute(doc(), { name: 'summary', id: null }, { ext: makeExt(dash, { now: () => NOW_ET4PM }) })).includes('last refreshed');
  // An unchanged allowance row for 20 hours (the Compare step skips unchanged datasets) is not a failed refresh.
  ok(!banner(fakeDash({ eval_allowance: ALLOW, refresh: refresh('2026-11-12T20:00:00Z', 12) })), 'fresh refresh clock, old allowance');
  eq(snapshotMs(fakeDash({ eval_allowance: ALLOW, refresh: refresh('2026-11-12T20:00:00Z', 12) })), Date.parse('2026-11-12T20:00:00Z'));
  ok(banner(fakeDash({ eval_allowance: ALLOW, refresh: refresh('2026-11-12T01:00:00Z', 12) })), 'old refresh clock warns');
  ok(!banner(fakeDash({ eval_allowance: ALLOW, refresh: refresh('2026-11-12T01:00:00Z', 24) })), 'a 24-hour interval allows 19 hours');
  ok(banner(fakeDash({ eval_allowance: ALLOW })), 'no refresh row falls back to the allowance time and 12 hours');
});
await test('R3 recommendation 9: a snapshot older than a refresh allows warns on every group; a fresh one does not', () => {
  const SNAP = (iso) => okData([{ measure: 'eval_spend_since_reset', points: 1, pace_room_points: 1, computed_at: iso }]);
  const old = fakeDash({ eval_allowance: SNAP('2026-11-12T01:16:00Z') });
  eq(snapshotMs(old), Date.parse('2026-11-12T01:16:00Z'));
  eq(staleHours(snapshotMs(old), NOW_ET4PM), 19);
  eq(staleHours(Date.parse('2026-11-12T20:00:00Z'), NOW_ET4PM), null, 'one hour old');
  eq(staleHours(NOW_ET4PM - 13 * 3600000, NOW_ET4PM), null, 'exactly at the limit is not past it');
  eq(staleHours(NOW_ET4PM - 13 * 3600000 - 1, NOW_ET4PM), 13);
  eq(staleHours(NaN, NOW_ET4PM), null, 'no snapshot is no claim');
  eq(staleHours(NOW_ET4PM - 20 * 3600000, NOW_ET4PM, 24), null, 'a 24-hour interval allows 20 hours');
  for (const name of ['summary', 'needs', 'changes', 'hooks', 'spend', 'activity']) {
    const t = flat(renderRoute(doc(), { name, id: null }, { ext: makeExt(old, { now: () => NOW_ET4PM }) }));
    ok(t.includes('This page was last refreshed Nov 11, 2026, 8:16 PM ET, 19 hours ago. It refreshes every 12 hours, so a refresh did not land.'), name + ': ' + t.slice(0, 200));
  }
  const fresh = fakeDash({ eval_allowance: SNAP('2026-11-12T20:00:00Z') });
  for (const name of ['summary', 'needs', 'activity']) ok(!flat(renderRoute(doc(), { name, id: null }, { ext: makeExt(fresh, { now: () => NOW_ET4PM }) })).includes('last refreshed'), name + ' fresh');
  ok(!flat(renderRoute(doc(), { name: 'summary', id: null }, {})).includes('last refreshed'), 'the public build has no banner');
});
await test('R12: panels say "As of <time ET>" and keep the dataset id in the hover text, never in the words', () => {
  const dash = needsDash({ routines: okData([routine('R1', 'OK')]) });
  const node = renderRoute(doc(), { name: 'activity', id: null }, { ext: makeExt(dash, { now: () => NOW_ET4PM }) });
  const t = flat(node);
  ok(t.includes('As of Nov 12, 2026, 3:00 PM ET.'), t.slice(0, 400));
  ok(!/dashboard snapshot|\(routines\)/.test(t), 'no dataset id in the visible text');
  ok(findAll(node, (n) => n.tag === 'p' && n.attrs.class === 'src' && n.attrs.title === 'routines').length === 1, 'the id is the hover text');
  const strings = fs.readFileSync(path.join(EXPLORER, 'src', 'private', 'strings.js'), 'utf8');
  ok(!/From the dashboard snapshot/.test(strings), 'no per-panel snapshot line left');
});

const CPULL = (n, title, head, merged, extra) => Object.assign({ repo: 'Adam-S-Daniel/adam-agentskills', number: n, title, head_ref: head, state: merged ? 'merged' : 'open',
  created_at: '2026-10-01T10:00:00Z', updated_at: merged || '2026-11-01T10:00:00Z', merged_at: merged || null, url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pull/' + n }, extra || {});
const CHDOC = () => doc({ generated_at: '2026-11-12T17:00:00Z',
  activity: { fetched_at: '2026-11-12T17:00:00Z', since: '2026-10-29T17:00:00Z', repos: [], issues: [], runs: [], pulls: [
    CPULL(142, 'Proposed workflow-path-audit SKILL.md edit (improvement run 20261110T1)', 'eval-improve/workflow-path-audit', '2026-11-10T15:00:00Z'),
    CPULL(111, 'New skill: demo-new', 'draft-skill/demo-new', '2026-11-07T15:00:00Z'),
    CPULL(120, 'Remove adam-coding-anywhere/old-skill: unused (removal policy)', 'retire-skill/old-skill', '2026-11-05T15:00:00Z'),
    CPULL(90, 'Proposed old-edit SKILL.md edit (improvement run r)', 'eval-improve/old-edit', '2026-10-01T15:00:00Z'),
    CPULL(150, 'Proposed open-edit SKILL.md edit (improvement run r)', 'eval-improve/open-edit', null),
    CPULL(7, 'Fix a typo', 'fix/typo', '2026-11-09T15:00:00Z')] },
  lessons: { date: '2026-11-10', items: [{ kind: 'new-skill', subject: 'demo-new', evidence_count: 7 }], left_out: null, issues: [] },
  removed_skills: [{ name: 'old-skill', plugin: 'adam-coding-anywhere', date: '2026-11-05', reverse_url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pulls?q=head%3Aretire-skill%2Fold-skill' },
    { name: 'ancient', plugin: 'p', date: '2026-09-28', reverse_url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pulls?q=head%3Aretire-skill%2Fancient' }],
  guidance: { sections: [], removed: [{ id: 'old-section', date: '2026-11-01', reverse_url: 'https://github.com/Adam-S-Daniel/_agent-guidance/pulls?q=head%3Aretire-guidance%2Fold-section' }] },
  agent_made: { rule_since: '2026-10-26T14:40:02Z', summary: {}, items: [
    { kind: 'check', id: 'demo-check', origin: 'agent', created: '2026-11-03T00:00:00Z', impact: { runs: 12, blocked: 3 } },
    { kind: 'skill', id: 'demo-new', origin: 'loop', created: '2026-11-07T00:00:00Z', impact: {} },
    { kind: 'section', id: 'person-made', origin: 'person', created: '2026-11-04T00:00:00Z', impact: {} }] } });
await test('R3 recommendation 5: the changes list is the last 30 days, newest first, every row with a reason, removals matched to their pull request', () => {
  const rows = changeRows(CHDOC());
  eq(rows.map((r) => r.kind + ':' + r.subject).join(','), 'editSkill:workflow-path-audit,newSkill:demo-new,removeSkill:old-skill,newCheck:demo-check,removeSection:old-section,removeSkill:ancient');
  ok(rows.every((r) => typeof r.why === 'string' && r.why.length > 10), 'every row has a reason');
  eq(rows.filter((r) => r.subject === 'old-skill').length, 1, 'the removal and its pull request are one row');
  eq(rows[2].pr.number, 120); eq(rows[2].undo.includes('retire-skill%2Fold-skill'), true);
  ok(rows[2].why.includes('not used'), 'the reason is read from the removal title: ' + rows[2].why);
  ok(rows[1].why.includes('7 lessons'), rows[1].why);
  ok(rows[3].why.includes('12 times') && rows[3].why.includes('blocked 3'), rows[3].why);
  eq(rows.filter((r) => r.subject === 'demo-new').length, 1, 'a new-skill pull request and the agent-made skill are one row');
  ok(!rows.some((r) => [90, 150, 7].includes(r.pr && r.pr.number)), 'an older, an open and a non-loop pull request are not listed');
  ok(!flat(renderRoute(CHDOC(), { name: 'changes', id: null }, {})).includes('ancient'), 'removed before the window: only in the removals-only view');
  eq(changeRows(doc({})).length, 0);
});
await test('R3 recommendation 5: the page shows the list with When, Change, Subject, Why, Pull request and Undo, and removals only on #/changes/removed', () => {
  const t = flat(renderRoute(CHDOC(), { name: 'changes', id: null }, {}));
  for (const w of ['What the loop changed', 'Edited skill', 'New skill', 'Removed skill', 'New git hook check', 'Removed guidance section', 'Why', 'Undo', 'Nov 10', 'adam-agentskills #142', 'Revert']) ok(t.includes(w), w);
  ok(t.indexOf('Nov 10') < t.indexOf('Nov 7') && t.indexOf('Nov 7') < t.indexOf('Nov 5'), 'newest first');
  const only = flat(renderRoute(CHDOC(), parseRoute('#/removed', '', Object.keys(ROUTE_GROUPS)), {}));
  ok(only.includes('old-skill') && only.includes('old-section') && only.includes('ancient'), 'every removal, whenever');
  ok(!only.includes('Edited skill') && !only.includes('New git hook check'), 'nothing else');
  const hrefs = findAll(renderRoute(CHDOC(), { name: 'changes', id: null }, {}), (n) => n.tag === 'a').map((n) => n.attrs.href);
  ok(hrefSet(hrefs).has('#/changes/removed') && hrefSet(hrefs).has('#/skills/workflow-path-audit'), 'the filter and the subject pages');
});
await test('R3 recommendation 5: the private build adds its live merged pull requests, once each', () => {
  const live = { repo: 'adam-agentskills', number: 142, title: 'Proposed workflow-path-audit SKILL.md edit (improvement run 20261110T1)', author: 'x', closed_at: '2026-11-10T15:00:00Z', url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pull/142' };
  const extra = { repo: 'adam-agentskills', number: 160, title: 'New skill: live-only', author: 'x', closed_at: '2026-11-11T15:00:00Z', url: 'https://github.com/Adam-S-Daniel/adam-agentskills/pull/160' };
  const ext = makeExt(fakeDash({ merged_prs: okData([live, extra]) }));
  const rows = changeRows(CHDOC(), ext.changePulls());
  eq(rows.filter((r) => r.pr && r.pr.number === 142).length, 1, 'the pull request the document already lists is not doubled');
  ok(rows.some((r) => r.subject === 'live-only'), 'a live-only pull request is added');
  eq(makeExt(fakeDash({})).changePulls().length, 0);
  ok(flat(renderRoute(CHDOC(), { name: 'changes', id: null }, { ext })).includes('live-only'));
});
await test('R2 and R7: the stage text lives on How the tests work; Changes holds the one trending table and Needs you none', () => {
  const stage = STRINGS.loopStages[0][1];
  ok(flat(renderRoute(doc(), { name: 'method', id: null }, {})).includes(stage), 'on How the tests work');
  ok(!flat(renderRoute(doc(), { name: 'changes', id: null }, {})).includes(stage), 'not on Changes');
  ok(!('loopPrsHeading' in STRINGS) && !('removedHeading' in STRINGS), 'the removed panels\' strings are gone');
});
await test('R4 and R5: Spend and use has no pull-request-by-week panel and no red CI panel, public or private', () => {
  const d = doc({ activity: { fetched_at: '2026-10-31T21:00:00Z', since: '2026-10-24T00:00:00Z', repos: ['Adam-S-Daniel/skills-evals'], issues: [],
    pulls: [CPULL(1, 'x', null, '2026-10-30T10:00:00Z')], runs: [{ repo: 'Adam-S-Daniel/skills-evals', run_id: 9, workflow: 'CI', title: 'CI', conclusion: 'failure', state: 'completed', created_at: '2026-10-30T10:00:00Z', url: 'https://github.com/Adam-S-Daniel/skills-evals/actions/runs/9' }] } });
  for (const ext of [null, makeExt(fakeDash({ usage_rows: okData([{ kind: 'repo', repo: 'r', week: '2026-10-26', prs_opened: 3 }]) }))]) {
    const t = flat(renderRoute(d, { name: 'spend', id: null }, { ext }));
    ok(!/Pull requests by week|Red CI runs|Red in CI runs|Pull request outcomes/.test(t), t.slice(0, 300));
  }
  ok(!('impactPrs' in STRINGS) && !('impactRed' in STRINGS), 'their strings are gone');
});
await test('PR 984: an old route name with anything after it still opens its new home', () => {
  const all = Object.keys(ROUTE_GROUPS);
  const at = (hash) => JSON.stringify(parseRoute(hash, '', all, 'needs'));
  eq(at('#/loop/x'), '{"name":"changes","id":null}');
  eq(at('#/loop/'), '{"name":"changes","id":null}');
  eq(at('#/impact/anything/else'), '{"name":"spend","id":null}');
  eq(at('#/ops/'), '{"name":"activity","id":null}');
  eq(at('#/removed/'), '{"name":"changes","id":"removed"}');
  eq(at('#/removed/x'), '{"name":"changes","id":"removed"}');
  eq(at('#/hooks/'), '{"name":"hooks","id":null}', 'a current route with a bare slash is unchanged');
});
await test('PR 984: every folded kind on Needs you says who acts', () => {
  const alerts = (n) => Array.from({ length: n }, (_, i) => ({ name: 'skill-' + i, kind: 'retire', text: 'due for removal', url: 'https://github.com/example-owner/r/issues/' + i, subject: 'skill' }));
  const fx = (kind) => Array.from({ length: 4 }, (_, i) => ({ finding_id: kind + i, kind, severity: kind === 'idle' ? 'medium' : 'high', subject: kind + i, url: 'https://github.com/example-owner/r/issues/' + i }));
  const dash = fakeDash({ half_built_issues: okData(Array.from({ length: 4 }, (_, i) => ({ key: 'h' + i, state: 'open', kind: 'broken', severity: 'high', title: 'T' + i, url: 'https://github.com/example-owner/r/issues/' + i, repo: 'r', age_days: 1 }))) });
  const groups = attentionGroups(attentionRows(dash, doc({ alerts: alerts(4), fixture_queue: { findings: fx('idle').concat(fx('broken')) } })));
  eq(groups.length, 4, groups.map((g) => g.kind).join('; '));
  for (const g of groups) ok(g.children && typeof g.note === 'string' && g.note.length > 20, g.kind + ' names who acts');
  ok(groups.find((g) => /idle/.test(g.kind)).note.includes('nothing for you') || groups.find((g) => /idle/.test(g.kind)).note.includes('Nothing for you'), 'the idle fixture note');
  // No inner scroll box: the note and the fold are not cut off.
  const node = needsPage(dash, doc({ alerts: alerts(4) }));
  ok(findAll(node, (n) => n.tag === 'div' && String(n.attrs && n.attrs.class || '').split(' ').includes('tall')).length === 0, 'no tall scroller on the attention table');
});
await test('PR 984: the changes list and the loop filter share one table of kinds; a branch decides when the document has one', () => {
  eq(LOOP_KINDS.map((k) => k.kind).join(','), 'editSkill,editGuidance,newSkill,removeSkill,removeSection');
  // Every kind's own branch and title are loop changes by both rules, and name that kind.
  const samples = { editSkill: ['eval-improve/x', 'Improve `x`: more'], editGuidance: ['eval-guidance-improve/x', 'Proposed x guidance edit'], newSkill: ['draft-skill/x', 'New skill: x'],
    removeSkill: ['retire-skill/x', 'Remove a/x: unused'], removeSection: ['retire-guidance/x', 'Retire guidance section x'] };
  for (const [kind, [ref, title]] of Object.entries(samples)) {
    ok(LOOP_BRANCH.test(ref) && LOOP_TITLE.test(title), kind + ' matches the shared patterns');
    eq(pullKind({ head_ref: ref, title: 'unrelated' }), kind, kind + ' by branch');
    eq(pullKind({ title }), kind, kind + ' by title');
    ok(isLoopPull({ head_ref: ref }) && isLoopPull({ title }), kind + ' is a loop pull');
  }
  // With a branch the title never decides: an ordinary branch titled like a loop change is no loop change.
  eq(pullKind({ head_ref: 'feature/x', title: 'New skill: x' }), null);
  ok(!isLoopPull({ head_ref: 'feature/x', title: 'New skill: x' }));
  eq(pullKind({ title: 'Fix a typo' }), null);
  ok(!STRINGS.changeWhy.checkRan(1, 1).includes('lesson') && !STRINGS.changeWhy.checkNew.includes('lesson'), 'no claim the data cannot back');
});
await test('PR 984: private Spend shows the weekly money once, the cost table folded, and says "list price" once', () => {
  const weeks = [{ week: '2026-11-09', eval_runs: 3, plan_meter_points: 1, api_usd: 14.41, thread_spend_usd: 335.49, run_usd: 91.75 }];
  const dash = fakeDash({ cost_benefit_summary: okData([{ key: 'k', label: 'Summary measure', value: 1, target: null, status: null, note: '' }]),
    cost_benefit_weeks: okData([{ week: '2026-11-09', run_count: 1, run_points_est: 1, api_usd: 1, build_usd: 1, build_points: 1, changes: 0, real_work_reach: 0, owner_messages: 0 }]) });
  const node = renderRoute(doc({ generated_at: '2026-11-12T17:00:00Z', spend: { generated_at: '2026-11-12T01:00:00Z', weeks } }), { name: 'spend', id: null }, { ext: makeExt(dash) });
  const t = flat(node);
  eq(t.split('list price').length - 1, 1, 'list price once: ' + t.slice(0, 300));
  ok(t.includes('Summary measure'), 'the summary measures stay');
  const folds = findAll(node, (n) => n.tag === 'details').filter((d) => flat(d).includes('Cost by week'));
  eq(folds.length, 1, 'the weekly cost table sits under a fold');
});
await test('R11: no Decisions column, cleanup list or decisions panel is built, and no string for them is left', () => {
  const dash = fakeDash({ cost_benefit_summary: okData([{ key: 'k', label: 'L', value: 1, target: null, status: null, note: '' }]),
    cost_benefit_weeks: okData([{ week: '2026-11-02', run_count: 1, run_points_est: 1, api_usd: 1, build_usd: 1, build_points: 1, changes: 0, real_work_reach: 0, owner_messages: 0, decisions: 4 }]),
    cleanup: okData([{ id: 'C1', item: 'Cleanup item text', done_when: 'x', status: 'Done' }]), decisions: okData([{ date: '2026-11-01', decision: 'A decision text', link: null }]) });
  const ext = makeExt(dash);
  const cost = flat(renderRoute(doc(), { name: 'spend', id: null }, { ext }));
  ok(cost.includes('Cost and benefit') && !cost.includes('Decisions'), 'the weekly table has no Decisions column');
  const ops = flat(renderRoute(doc(), { name: 'activity', id: null }, { ext }));
  ok(!/Cleanup list|Your decisions|Cleanup item text|A decision text/.test(ops), 'no cleanup or decisions panel');
  const priv = fs.readFileSync(path.join(EXPLORER, 'src', 'private', 'strings.js'), 'utf8');
  ok(!/cleanupHeading|decisionsHeading|colDecisions/.test(priv));
});
await test('R3 and R11 class guard: every dataset the private source reads is in datasets.json, and every dataset there is read', () => {
  const defined = Object.keys(JSON.parse(fs.readFileSync(DATASETS, 'utf8')));
  const read = new Set();
  const dir = path.join(EXPLORER, 'src');
  (function scan(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { scan(p); continue; }
      if (!p.endsWith('.js')) continue;
      (function walk(n) {
        if (!n || typeof n.type !== 'string') return;
        if (n.type === 'CallExpression' && n.callee.type === 'Identifier' && ['rowsOf', 'some', 'ok'].includes(n.callee.name)) {
          const a = n.arguments[n.callee.name === 'ok' ? 0 : 1];
          if (a && a.type === 'Literal' && typeof a.value === 'string') read.add(a.value);
        }
        if (n.type === 'CallExpression' && n.callee.type === 'MemberExpression' && n.callee.property.name === 'loader' && n.arguments[0] && n.arguments[0].type === 'Literal') read.add(n.arguments[0].value);
        for (const [k, v] of Object.entries(n)) { if (k === 'type') continue; if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') walk(v); }
      })(acorn.parse(fs.readFileSync(p, 'utf8'), { ecmaVersion: 'latest', sourceType: 'module' }));
    }
  })(dir);
  eq([...read].filter((id) => !defined.includes(id)).join(','), '', 'read but not defined');
  // Read by name elsewhere: the explorer documents by the adapter, budget and roster by makeExt's helpers.
  const apart = new Set([DATASET_ID, PRIVATE_DATASET_ID]);
  eq(defined.filter((id) => !read.has(id) && !apart.has(id)).join(','), '', 'defined but never read');
});
await test('R3: the dashboard runtime keeps no loop_* dataset, gate, cleanup or decisions id', () => {
  const defined = Object.keys(JSON.parse(fs.readFileSync(DATASETS, 'utf8')));
  for (const gone of ['cleanup', 'decisions', 'gate', 'loop_stages', 'loop_grid', 'loop_lanes', 'loop_gaps']) ok(!defined.includes(gone), gone);
});
await test('recommendation 6: spend shows this week and last week side by side in dollars, with week starts in Eastern time and the share that bought nothing', () => {
  const weeks = [{ week: '2026-11-02', eval_runs: 5, plan_meter_points: 2, api_usd: 200, thread_spend_usd: 4000, run_usd: 900 },
    { week: '2026-11-09', eval_runs: 3, plan_meter_points: 1, api_usd: 14.41, thread_spend_usd: 335.49, run_usd: 91.75 },
    { week: '2026-10-26', eval_runs: 1, plan_meter_points: 1, api_usd: 1, thread_spend_usd: 1, run_usd: 1 }];
  const two = spendWeeks(doc({ spend: { weeks } }));
  eq(two.map((w) => w.week).join(','), '2026-11-09,2026-11-02', 'the two newest, newest first');
  eq(two[0].total, 91.75 + 335.49 + 14.41);
  const utility = [U('2026-11-10', 'decisive', 10, 59), U('2026-11-10', 'discarded', 4, 25, 'fixture_changed'), U('2026-11-10', 'discarded', 3, 15, 'fixture_off_main'), U('2026-11-10', 'stranded', 1, 1, 'subject_changed')];
  const d = doc({ generated_at: '2026-11-12T17:00:00Z', skills: [{ name: 'a', run_utility: utility }], spend: { generated_at: '2026-11-12T01:00:00Z', weeks } });
  const share = noUseShare(d, Date.parse(d.generated_at));
  eq(Math.round(share.share * 100), 41);
  eq(share.top.map((x) => x[0]).join(','), 'fixture changed,fixture no longer scheduled');
  const t = flat(renderRoute(d, { name: 'spend', id: null }, {}));
  ok(t.includes('This week (from Nov 9, 2026, 12:00 PM ET)') && t.includes('Last week (from Nov 2, 2026, 12:00 PM ET)'), 'week starts in ET: ' + t.slice(0, 600));
  ok(t.includes('$91.75 · 1.0 points') && t.includes('$335.49') && t.includes('$14.41') && t.includes('$441.65'), 'this week\'s parts and total');
  ok(t.includes('In the last 30 days 41% of test dollars bought nothing ($41.00 of $100.00), mostly fixture changed ($25.00) and fixture no longer scheduled ($15.00).'), t);
  ok(t.includes('Dollars are list price, not what is paid.'), 'said once');
  eq(t.split('not what is paid').length - 1, 1, 'once');
  const old = flat(renderRoute(doc({ spend: { generated_at: '2026-11-12T01:00:00Z', weeks: weeks.map((w) => ({ week: w.week, eval_runs: 1, plan_meter_points: 1, api_usd: 1, thread_spend_usd: 1 })) } }), { name: 'spend', id: null }, {}));
  ok(old.includes('Week (from') && !old.includes('In the last 30 days'), 'data without run_usd or a ledger still renders, with no total or share');
  eq(spendWeeks(doc({ spend: { weeks: [{ week: '2026-11-09', api_usd: 1, thread_spend_usd: 1 }] } }))[0].total, null, 'a missing part is no total');
  // Old data does not call an old week this one: the label follows the data's own time.
  const stale = flat(renderRoute(doc({ generated_at: '2026-11-25T17:00:00Z', spend: { weeks } }), { name: 'spend', id: null }, {}));
  ok(!stale.includes('This week (from') && !stale.includes('Last week (from') && stale.includes('Week (from Nov 9, 2026, 12:00 PM ET)'), stale.slice(0, 500));
  const prior = flat(renderRoute(doc({ generated_at: '2026-11-17T12:00:00Z', spend: { weeks } }), { name: 'spend', id: null }, {}));
  ok(prior.includes('Last week (from Nov 9, 2026, 12:00 PM ET)') && !prior.includes('This week (from'), 'the day before the new week starts: still last week');
});
await test('recommendation 19: every route of the old six groups still opens a page, and each group leads with one question', () => {
  const all = Object.keys(ROUTE_GROUPS);
  for (const hash of ['#/loop', '#/impact', '#/ops', '#/removed', '#loop', '#impact', '#overview', '#costbenefit', '#evals', '#cleanup', '#decisions', '#console', '#/hooks', '#/skills/x', '#/method']) {
    const r = parseRoute(hash, '', all, 'needs');
    ok(r.name !== 'summary', hash + ' leaves Summary: ' + JSON.stringify(r));
    ok(textOf(renderRoute(doc(), r, { ext: makeExt(fakeDash({})) })).length > 0, hash + ' renders');
  }
  eq(ROUTE_GROUPS.results.join(','), 'hooks,skills,guidance,method');
  ok(!Object.values(ROUTE_GROUPS).some((g) => g.includes('removed')), 'Removed is no route');
  eq(textOf(renderRoute(doc(), { name: 'hooks', id: null }, {})).includes('Removed'), false, 'no Removed sub-tab');
  const tabs = findAll(renderRoute(doc(), { name: 'hooks', id: null }, {}), (n) => n.tag === 'a' && /^sub-/.test(n.attrs.id || '')).map((n) => n.attrs.id);
  eq(tabs.join(','), 'sub-hooks,sub-skills,sub-guidance,sub-method');
});

await test('the routine line counts every row of the routine table: healthy, not run yet and needing a look add up', () => {
  const dash = fakeDash({ routines: okData([routine('A', 'OK'), routine('B', 'Not run yet'), routine('C', 'Late')]), eval_allowance: SNAP_OK(), budget: BUDGET });
  const node = needsPage(dash);
  ok(flat(node).includes('1 of 3 routines healthy; 1 late, failing or to check; 1 not run yet.'), flat(node));
  const sec = findAll(node, (n) => n.tag === 'section' && textOf(n).includes('Routine health'))[0];
  eq(findAll(sec, (n) => n.tag === 'tbody').reduce((t, b) => t + findAll(b, (n) => n.tag === 'tr').length, 0), 3, 'the table lists all three');
  ok(!flat(needsPage(needsDash())).includes('not run yet'), 'no clause when none');
});

for (const f of failures) console.log('FAIL ' + f);
console.log(passed + ' passed, ' + failures.length + ' failed');
process.exit(failures.length ? 1 : 0);
