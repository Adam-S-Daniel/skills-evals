/* The project dashboard's data source: the same document latest.json holds,
   read from the Dashboard dataset `explorer` with dash.data(), re-read on
   every dash.onData(). Not wired into dashboard/page yet. */
import { validateDoc } from '../core/validate.js';

export const DATASET_ID = 'explorer';

/* One read of the dataset, in loadData's result shape. dash.data(id) answers
   { status, data }: only status 'ok' carries a document; 'loading' is not a
   failure yet, anything else is. */
export function readDashboard(dash, id) {
  const ds = id || DATASET_ID;
  let d;
  try { d = dash.data(ds); } catch (e) { return { ok: false, kind: 'fetch', url: null }; }
  if (!d || typeof d !== 'object') return { ok: false, kind: 'fetch', url: null };
  if (d.status === 'loading') return { ok: false, kind: 'loading', url: null };
  if (d.status !== 'ok') return { ok: false, kind: 'fetch', url: null };
  const v = validateDoc(d.data);
  if (!v.ok) return Object.assign({ url: null }, v);
  return { ok: true, doc: d.data, url: null };
}

/* The adapter boot() reads. It reports now, then again on every onData;
   a 'loading' read reports nothing, so the page keeps what it shows. */
export function dashboardSource(dash, id) {
  return {
    start({ onDoc, onFail }) {
      const push = () => {
        const res = readDashboard(dash, id);
        if (res.ok) onDoc(res.doc, null);
        else if (res.kind !== 'loading') onFail(res);
      };
      dash.onData(push);
      push();
    }
  };
}
