// Builds three pages from src/, each ONE self-contained file with its entry
// bundled inline and no external scripts:
//   ../tool/index.html            the public Evals Explorer (template/public.html)
//   ../dashboard/page/index.html  the private dashboard page (template/private.html)
//   dist/artifact/index.html      the public Explorer as a claude.ai artifact
//                                 (template/public.html), reading latest.json
//                                 beside it on its own origin
// All share template/base.css.
//   node build.js          write every page
//   node build.js --check  exit 1 when any committed page differs from a build
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'tool', 'index.html');
const TEMPLATE = path.join(HERE, 'template', 'public.html');
const PRIVATE_OUT = path.join(HERE, '..', 'dashboard', 'page', 'index.html');
const PRIVATE_TEMPLATE = path.join(HERE, 'template', 'private.html');
const BASE_CSS = path.join(HERE, 'template', 'base.css');
const ARTIFACT_OUT = path.join(HERE, 'dist', 'artifact', 'index.html');
const WEB_ADAPTER = path.join(HERE, 'src', 'adapters', 'web.js');
const ARTIFACT_ADAPTER = path.join(HERE, 'src', 'adapters', 'artifact.js');

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
  const whitespace = opts && typeof opts.minifyWhitespace === 'boolean' ? opts.minifyWhitespace : entry === 'private.js';
  const res = await build({
    plugins: entry === 'artifact.js' ? [artifactAdapter] : [],
    entryPoints: [path.join(HERE, 'src', 'entries', entry)],
    bundle: true,
    write: false,
    format: 'iife',
    platform: 'browser',
    target: 'es2020',
    charset: 'utf8',
    // The console stores the private page as one ArtifactData document, which
    // holds at most 262,144 bytes once JSON-serialized. Whitespace only: names
    // and syntax stay readable, and the public bundles are unchanged.
    minifyWhitespace: whitespace,
    legalComments: 'none',
    // The page was a strict-mode script before the split; keep it one.
    banner: { js: "'use strict';" },
    logLevel: 'silent'
  });
  return res.outputFiles[0].text;
}

/* A template with its CSS and one bundle filled in. */
function fill(templatePath, js, vars) {
  if (/<\/script/i.test(js)) throw new Error('the bundle contains </script, which would end the inline script early');
  const css = fs.readFileSync(BASE_CSS, 'utf8').replace(/\n$/, '');
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

export async function buildPrivatePage() {
  return fill(PRIVATE_TEMPLATE, await bundle('private.js'), {});
}

export async function buildArtifactPage() {
  const { DEFAULT_DATA_URL } = await import('./src/adapters/artifact.js');
  return fill(TEMPLATE, await bundle('artifact.js'), { DATA_URL: DEFAULT_DATA_URL });
}

export const OUTPUTS = [
  { name: 'tool/index.html', out: OUT, make: buildPublicPage },
  { name: 'dashboard/page/index.html', out: PRIVATE_OUT, make: buildPrivatePage },
  { name: 'explorer/dist/artifact/index.html', out: ARTIFACT_OUT, make: buildArtifactPage }
];

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let stale = 0;
  for (const o of OUTPUTS) {
    const page = await o.make();
    if (process.argv.includes('--check')) {
      const committed = fs.existsSync(o.out) ? fs.readFileSync(o.out, 'utf8') : '';
      if (committed !== page) {
        console.error(o.name + ' is out of date with explorer/src: run `npm run build` in explorer/ and commit every page');
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
