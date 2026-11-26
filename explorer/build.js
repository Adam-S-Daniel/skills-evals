// Builds three pages from src/, each ONE self-contained file with its entry
// bundled inline and no external scripts:
//   ../tool/index.html            the public Improvement Loop Explorer (template/public.html)
//   ../dashboard/page/index.html  the private dashboard page (template/private.html)
//   ../dashboard/page/datasets.json  its dataset list, with the repo lists written from display.json
//   dist/artifact/index.html      the public Explorer as a claude.ai artifact
//                                 (template/public.html), reading latest.json
//                                 beside it on its own origin
// All share template/base.css and read the time zone and repos from display.json.
//   node build.js          write every page
//   node build.js --check  exit 1 when any committed output differs from a build
import { build } from 'esbuild';
import { parse, tokTypes } from 'acorn';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateDisplay } from './display-check.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'tool', 'index.html');
const TEMPLATE = path.join(HERE, 'template', 'public.html');
const PRIVATE_OUT = path.join(HERE, '..', 'dashboard', 'page', 'index.html');
const PRIVATE_TEMPLATE = path.join(HERE, 'template', 'private.html');
const BASE_CSS = path.join(HERE, 'template', 'base.css');
const ARTIFACT_OUT = path.join(HERE, 'dist', 'artifact', 'index.html');
const WEB_ADAPTER = path.join(HERE, 'src', 'adapters', 'web.js');
const ARTIFACT_ADAPTER = path.join(HERE, 'src', 'adapters', 'artifact.js');
const DISPLAY_FILE = path.join(HERE, 'display.json');
const DATASETS_OUT = path.join(HERE, '..', 'dashboard', 'page', 'datasets.json');

/* explorer/display.json, validated: the time zone every page displays and the
   repositories the private page lists. A missing or invalid key throws a
   message naming the file and key. `file` is for the tests. */
export function loadDisplay(file) {
  const f = file || DISPLAY_FILE;
  const name = f === DISPLAY_FILE ? 'explorer/display.json' : f;
  let raw;
  try { raw = fs.readFileSync(f, 'utf8'); } catch (e) { throw new Error(name + ' is missing: create it with the keys "time_zone" (an IANA zone such as "Europe/Berlin") and "issue_repos" (["owner/repo", ...])'); }
  let cfg;
  try { cfg = JSON.parse(raw); } catch (e) { throw new Error(name + ' is not valid JSON: ' + e.message); }
  return validateDisplay(cfg, name);
}

/* Serves explorer/display.json (or `file`, for a test) to every import of it.
   Only the private page lists issues, so the other bundles get the time zone
   and the first repository (the one they read data from), not the rest. */
function displayPlugin(file, keepRepos) {
  return {
    name: 'display-config',
    setup(b) {
      b.onResolve({ filter: /(^|\/)display\.json$/ }, (args) =>
        path.resolve(args.resolveDir, args.path) === DISPLAY_FILE ? { path: DISPLAY_FILE, namespace: 'display-config' } : undefined);
      b.onLoad({ filter: /.*/, namespace: 'display-config' }, () => {
        const d = loadDisplay(file);
        return { contents: JSON.stringify({ time_zone: d.timeZone, issue_repos: keepRepos ? d.issueRepos : d.issueRepos.slice(0, 1) }), loader: 'json' };
      });
    }
  };
}

/* Resolves every import of adapters/web.js to adapters/artifact.js, so the
   artifact bundle holds no raw.githubusercontent.com URL: views and app.js
   import DEFAULT_DATA_URL from web.js too. */
const artifactAdapter = {
  name: 'artifact-adapter',
  setup(b) {
    b.onResolve({ filter: /(^|\/)web\.js$/ }, (args) =>
      path.resolve(args.resolveDir, args.path) === WEB_ADAPTER ? { path: ARTIFACT_ADAPTER } : undefined);
  }
};

/* The bundle of one entry, as a string. Exported for test/run.js. */
export async function bundle(entry, opts) {
  const o = opts || {};
  const flag = (name, dflt) => (typeof o[name] === 'boolean' ? o[name] : dflt);
  const priv = entry === 'private.js';
  const res = await bundleResult(entry, {
    // Syntax and whitespace everywhere; identifiers only for the private page,
    // which the console stores as one ArtifactData document of at most 262,144
    // bytes once JSON-serialized. Identifier names stay in the public pages.
    minifySyntax: flag('minifySyntax', true), minifyWhitespace: flag('minifyWhitespace', true), minifyIdentifiers: flag('minifyIdentifiers', priv)
  });
  return res.outputFiles[0].text;
}

/* The esbuild result (output text and, for test/run.js, the metafile of which
   input files went in). */
export async function bundleResult(entry, min, displayFile) {
  loadDisplay(displayFile);  // fails the build before esbuild runs
  return build({
    plugins: (entry === 'artifact.js' ? [artifactAdapter] : []).concat([displayPlugin(displayFile, entry === 'private.js')]),
    metafile: true,
    entryPoints: [path.join(HERE, 'src', 'entries', entry)],
    bundle: true,
    write: false,
    format: 'iife',
    platform: 'browser',
    target: 'es2020',
    charset: 'utf8',
    minifyWhitespace: min.minifyWhitespace,
    minifySyntax: min.minifySyntax,
    minifyIdentifiers: min.minifyIdentifiers,
    legalComments: 'none',
    // The page was a strict-mode script before the split; keep it one.
    banner: { js: "'use strict';" },
    logLevel: 'silent'
  });
}

/* One module's bundle as an IIFE assigned to `globalName`, with the display
   config read from `displayFile`. For test/run.js to format under another zone. */
export async function bundleModule(file, globalName, displayFile) {
  loadDisplay(displayFile);
  const res = await build({
    plugins: [displayPlugin(displayFile, true)],
    entryPoints: [file], bundle: true, write: false, format: 'iife', globalName, platform: 'browser', target: 'es2020', charset: 'utf8', logLevel: 'silent'
  });
  return res.outputFiles[0].text;
}

/* A template with its CSS and one bundle filled in. */
/* The private page sits in a dashboard pane that can be far narrower than the
   window (beside a chat, or with Sources open), so its layout answers to its
   own width: every width @media in base.css becomes an @container query on
   #ex-root, which private.html makes a container. */
export function widthQueriesToContainer(css) {
  return css.replace(/@media \((max|min)-width:/g, '@container ($1-width:');
}

function fill(templatePath, js, vars, opts) {
  if (/<\/script/i.test(js)) throw new Error('the bundle contains </script, which would end the inline script early');
  let css = fs.readFileSync(BASE_CSS, 'utf8').replace(/\n$/, '');
  // The private page has a hard size cap, so its stylesheet ships without its
  // comments (a comment is a lexical token; no rule is touched).
  if (opts && opts.container) css = widthQueriesToContainer(css).replace(/\/\*[\s\S]*?\*\/\n?/g, '');
  let tpl = fs.readFileSync(templatePath, 'utf8');
  const c = tpl.split('/*__CSS__*/');
  if (c.length !== 2) throw new Error(templatePath + ' must hold exactly one /*__CSS__*/ marker');
  tpl = c[0] + css + c[1];
  const parts = tpl.split('/*__BUNDLE__*/');
  if (parts.length !== 2) throw new Error(templatePath + ' must hold exactly one /*__BUNDLE__*/ marker');
  // split/join, never String.replace: a `$&` in the bundle must stay literal.
  let head = parts[0];
  for (const [k, v] of Object.entries(vars || {})) head = head.split('{{' + k + '}}').join(v);
  return head + js.replace(/\n$/, '') + parts[1];
}

export async function buildPublicPage() {
  const { DEFAULT_DATA_URL } = await import('./src/adapters/web.js');
  return fill(TEMPLATE, await bundle('public.js'), { DATA_URL: DEFAULT_DATA_URL });
}

/* The console stores the private page as a JSON string, where every double
   quote costs two bytes. esbuild writes string literals with double quotes,
   so each literal that serializes smaller in single quotes is rewritten that
   way. Literals are the string tokens of a real parse of the bundle, never a pattern match. */
export function singleQuoted(js) {
  const edits = [];
  parse(js, { ecmaVersion: 'latest', sourceType: 'script', onToken(tok) {
    if (tok.type !== tokTypes.string || js[tok.start] !== '"') return;
    const inner = js.slice(tok.start + 1, tok.end - 1);
    let out = '';
    for (let i = 0; i < inner.length; i++) {
      const c = inner[i];
      if (c === '\\') { const next = inner[++i]; out += next === '"' ? '"' : c + next; }
      else out += c === "'" ? "\\'" : c;
    }
    const next = "'" + out + "'";
    if (JSON.stringify(next).length < JSON.stringify(js.slice(tok.start, tok.end)).length) edits.push([tok.start, tok.end, next]);
  } });
  edits.sort((a, b) => b[0] - a[0]);
  for (const [start, end, text] of edits) js = js.slice(0, start) + text + js.slice(end);
  return js;
}

export async function buildPrivatePage() {
  return fill(PRIVATE_TEMPLATE, singleQuoted(await bundle('private.js')), {}, { container: true });
}

export async function buildArtifactPage() {
  const { DEFAULT_DATA_URL } = await import('./src/adapters/artifact.js');
  return fill(TEMPLATE, await bundle('artifact.js'), { DATA_URL: DEFAULT_DATA_URL });
}

/* dashboard/page/datasets.json is read by the console, which cannot read
   config, so the entries that name the repositories are written from
   issue_repos here: the queries and the sentences that list them. */
const COUNT_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
export function applyIssueRepos(datasets, repos) {
  const first = repos[0].split('/');
  const short = repos.map((r) => r.split('/')[1]);
  const list = short.length === 1 ? short[0] : short.slice(0, -1).join(', ') + ' and ' + short[short.length - 1];
  const qualifiers = repos.map((r) => 'repo:' + r).join(' ');
  const same = (COUNT_WORDS[repos.length] || String(repos.length)) + ' repos';
  const set = (id, fn) => {
    if (!datasets[id]) throw new Error('dashboard/page/datasets.json has no dataset "' + id + '", which build.js writes from issue_repos');
    fn(datasets[id]);
  };
  set('budget', (d) => { d.request.args.owner = first[0]; d.request.args.repo = first[1]; });
  set('eval_ingests', (d) => { d.source.args.owner = first[0]; d.source.args.repo = first[1]; });
  set('merged_prs', (d) => {
    d.source.args.query = 'is:merged ' + qualifiers;
    d.description = d.description.replace(/in the same [a-z0-9]+ repos/, 'in the same ' + same);
  });
  set('open_prs', (d) => {
    d.source.args.query = 'is:open ' + qualifiers;
    d.description = d.description.replace(/in [^()]*? \(head branch rule/, 'in ' + list + ' (head branch rule');
  });
  set('open_issues', (d) => {
    d.source.args.owner = first[0];
    d.source.args.repo = first[1];
    d.description = d.description.replace(/in [^()]*? \(title and label rule/, 'in ' + list + ' (title and label rule');
  });
  return datasets;
}
export function buildDatasets(display) {
  const d = display || loadDisplay();
  const cur = JSON.parse(fs.readFileSync(DATASETS_OUT, 'utf8'));
  return JSON.stringify(applyIssueRepos(cur, d.issueRepos), null, 1) + '\n';
}

export const OUTPUTS = [
  { name: 'tool/index.html', out: OUT, make: buildPublicPage },
  { name: 'dashboard/page/index.html', out: PRIVATE_OUT, make: buildPrivatePage },
  { name: 'explorer/dist/artifact/index.html', out: ARTIFACT_OUT, make: buildArtifactPage },
  { name: 'dashboard/page/datasets.json', out: DATASETS_OUT, make: async () => buildDatasets() }
];

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let stale = 0;
  try { loadDisplay(); } catch (e) { console.error(e.message); process.exit(1); }
  for (const o of OUTPUTS) {
    const page = await o.make();
    if (process.argv.includes('--check')) {
      const committed = fs.existsSync(o.out) ? fs.readFileSync(o.out, 'utf8') : '';
      if (committed !== page) {
        console.error(o.name + ' is out of date with explorer/src: run `npm run build` in explorer/ and commit every output');
        stale += 1;
      } else console.log(o.name + ' matches a fresh build of explorer/src');
    } else {
      fs.mkdirSync(path.dirname(o.out), { recursive: true });
      fs.writeFileSync(o.out, page);
      console.log('wrote ' + o.name + ' (' + page.length + ' characters)');
    }
  }
  if (stale) process.exit(1);
}
