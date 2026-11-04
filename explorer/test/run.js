// Tests for explorer/: the dashboard adapter, the public bundle's contents and
// the build's output. Plain Node plus the pinned devDependencies, no network.
// Run: npm test   (in explorer/; exits nonzero on any failure)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as acorn from 'acorn';
import { bundle, buildPublicPage } from '../build.js';
import { readDashboard, dashboardSource, DATASET_ID } from '../src/adapters/dashboard.js';
import { DEFAULT_DATA_URL, DATA_URL_PREFIX, allowedDataUrl } from '../src/adapters/web.js';
import { DATA_REPO } from '../src/config.js';
import { SCHEMA_VERSION } from '../src/core/rules.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const EXPLORER = path.resolve(HERE, '..');
const REPO = path.resolve(EXPLORER, '..');
const PAGE = path.join(REPO, 'tool', 'index.html');
const DATASETS = path.join(REPO, 'dashboard', 'page', 'datasets.json');

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
await test('the public bundle leaves out the dashboard adapter and the private entry', () => {
  ok(!publicJs.includes('src/adapters/dashboard.js') && !publicJs.includes('src/entries/private.js'), 'module markers');
  ok(!stringsIn(publicJs).includes(DATASET_ID), 'no explorer dataset id');
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

for (const f of failures) console.log('FAIL ' + f);
console.log(passed + ' passed, ' + failures.length + ' failed');
process.exit(failures.length ? 1 : 0);
