/* One cache-busted read of the explorer document, validated. Shared by the
   web adapter (web.js) and the artifact adapter (artifact.js), which differ
   only in which URL they read. */
import { validateDoc } from '../core/validate.js';

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
