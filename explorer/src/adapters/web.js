/* The public page's data source: latest.json on raw.githubusercontent.com,
   read from this repository's persistent/eval-results branch. The owner and
   repository come from config.js alone. */
import { DATA_REPO } from '../config.js';
import { validateDoc } from '../core/validate.js';

export const DEFAULT_DATA_URL =
  'https://raw.githubusercontent.com/' + DATA_REPO + '/persistent/eval-results/explorer/latest.json';
export const DATA_URL_PREFIX = 'https://raw.githubusercontent.com/' + DATA_REPO + '/';

export function allowedDataUrl(candidate) {
  if (typeof candidate !== 'string' || !candidate) return null;
  let u;
  try { u = new URL(candidate); } catch (e) { return null; }
  if (u.username || u.password) return null;
  if (u.protocol === 'http:' && (u.hostname === 'localhost' || u.hostname === '127.0.0.1')
      && (candidate.startsWith('http://localhost') || candidate.startsWith('http://127.0.0.1'))) return u.href;
  if (u.protocol === 'https:' && u.hostname === 'raw.githubusercontent.com' && !u.port
      && candidate.startsWith(DATA_URL_PREFIX) && u.href.startsWith(DATA_URL_PREFIX)) return u.href;
  return null;
}

/* Returns {url} for the file to read, or {error:'badurl', url} for a refused override. */
export function dataUrlFromSearch(search) {
  const q = new URLSearchParams(search || '');
  if (!q.has('data')) return { url: DEFAULT_DATA_URL };
  const ok = allowedDataUrl(q.get('data'));
  return ok ? { url: ok } : { error: 'badurl', url: DEFAULT_DATA_URL };
}

export function cacheBust(url, stamp) {
  return url + (url.includes('?') ? '&' : '?') + 'v=' + encodeURIComponent(String(stamp));
}

export async function loadData(url, fetchFn, stamp) {
  let res;
  try {
    res = await fetchFn(cacheBust(url, stamp), { cache: 'no-store' });
  } catch (e) {
    return { ok: false, kind: 'fetch', url: url };
  }
  if (!res || !res.ok) return { ok: false, kind: 'fetch', url: url };
  let doc;
  try { doc = await res.json(); } catch (e) { return { ok: false, kind: 'parse', url: url }; }
  const v = validateDoc(doc);
  if (!v.ok) return Object.assign({ url: url }, v);
  return { ok: true, doc: doc, url: url };
}

/* The adapter boot() reads: the ?data override (refused unless allowed),
   then one fetch. */
export function webSource(fetchFn, search, stamp) {
  return {
    start({ onDoc, onFail }) {
      const pick = dataUrlFromSearch(search);
      if (pick.error) { onFail({ kind: 'badurl', url: pick.url }); return; }
      loadData(pick.url, fetchFn, stamp).then((res) => {
        if (!res.ok) { onFail(res); return; }
        onDoc(res.doc, pick.url);
      });
    }
  };
}
