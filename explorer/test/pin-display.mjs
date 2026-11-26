/* A Node module-loader hook: an import of explorer/display.json (from
   src/core/display.js) resolves to test/display.test.json instead. */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const COMMITTED = path.join(HERE, '..', 'display.json');
const FIXTURE = pathToFileURL(path.join(HERE, 'display.test.json')).href;

export async function resolve(specifier, context, next) {
  const r = await next(specifier, context);
  if (r.url.startsWith('file:') && path.resolve(fileURLToPath(r.url)) === COMMITTED) return { ...r, url: FIXTURE };
  return r;
}
