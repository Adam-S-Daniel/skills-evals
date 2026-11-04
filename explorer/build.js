// Builds tool/index.html from src/ as ONE self-contained file: the template's
// head and CSS, with the public entry bundled inline. No external scripts.
//   node build.js          write ../tool/index.html
//   node build.js --check  exit 1 when the committed file differs from a build
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'tool', 'index.html');
const TEMPLATE = path.join(HERE, 'template', 'public.html');

/* The bundle of one entry, as a string. Exported for test/run.js. */
export async function bundle(entry) {
  const res = await build({
    entryPoints: [path.join(HERE, 'src', 'entries', entry)],
    bundle: true,
    write: false,
    format: 'iife',
    platform: 'browser',
    target: 'es2020',
    charset: 'utf8',
    legalComments: 'none',
    // The page was a strict-mode script before the split; keep it one.
    banner: { js: "'use strict';" },
    logLevel: 'silent'
  });
  return res.outputFiles[0].text;
}

export async function buildPublicPage() {
  const { DEFAULT_DATA_URL } = await import('./src/adapters/web.js');
  const js = await bundle('public.js');
  if (/<\/script/i.test(js)) throw new Error('the bundle contains </script, which would end the inline script early');
  const tpl = fs.readFileSync(TEMPLATE, 'utf8');
  const parts = tpl.split('/*__BUNDLE__*/');
  if (parts.length !== 2) throw new Error('the template must hold exactly one /*__BUNDLE__*/ marker');
  // split/join, never String.replace: a `$&` in the bundle must stay literal.
  return parts[0].split('{{DATA_URL}}').join(DEFAULT_DATA_URL) + js.replace(/\n$/, '') + parts[1];
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const page = await buildPublicPage();
  if (process.argv.includes('--check')) {
    const committed = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : '';
    if (committed !== page) {
      console.error('tool/index.html is out of date with explorer/src: run `npm run build` in explorer/ and commit both');
      process.exit(1);
    }
    console.log('tool/index.html matches a fresh build of explorer/src');
  } else {
    fs.writeFileSync(OUT, page);
    console.log('wrote tool/index.html (' + page.length + ' characters)');
  }
}
