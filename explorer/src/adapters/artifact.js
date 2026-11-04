/* The artifact page's data source: latest.json beside the page, on the
   page's own origin. A claude.ai artifact's content security policy allows
   connect-src 'self' blob: only, so this adapter reads one relative URL and
   takes no ?data= override. It exports every name web.js exports, because
   build.js puts it in web.js's place for the whole artifact bundle, and so
   no raw.githubusercontent.com URL reaches that bundle. */
import { cacheBust, loadData } from './load.js';

export { cacheBust, loadData };

export const DEFAULT_DATA_URL = 'latest.json';

/* No override is ever allowed. */
export function allowedDataUrl() { return null; }

/* Always the file beside the page, whatever the query string says. */
export function dataUrlFromSearch() { return { url: DEFAULT_DATA_URL }; }

/* The adapter boot() reads: one fetch of latest.json. */
export function webSource(fetchFn, search, stamp) {
  return {
    start({ onDoc, onFail }) {
      loadData(DEFAULT_DATA_URL, fetchFn, stamp).then((res) => {
        if (!res.ok) { onFail(res); return; }
        onDoc(res.doc, DEFAULT_DATA_URL);
      });
    }
  };
}
