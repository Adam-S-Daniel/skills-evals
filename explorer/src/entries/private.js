/* The private project dashboard (dashboard/page/index.html, a claude.ai
   Dashboard artifact): every public view, read from the `explorer` dataset,
   plus the Needs you group and the panels the dashboard's own datasets add.
   Private-skill results (dataset `explorer_private`) merge in with a
   "Private" badge. Never imported by public.js. */
import { EXPORTS as PUBLIC } from './shared.js';
import { useVoice } from '../core/strings.js';
import { readDashboard, dashboardSource, DATASET_ID } from '../adapters/dashboard.js';
import { boot } from '../app.js';
import { registerLoaders } from '../private/loaders.js';
import { mergePrivate } from '../private/merge.js';
import { makeExt, attentionRows, attentionGroups, capUse, routineHealth, snapshotMs, staleHours } from '../private/views.js';
import { rowsOf, some } from '../private/datasets.js';

export const PRIVATE_DATASET_ID = 'explorer_private';
export const GROUPS = ['summary', 'needs', 'changes', 'results', 'spend', 'activity'];

/* The adapter the private page boots from: the public document, with the
   private one merged in whenever it has loaded. */
export function privateSource(dash) {
  const base = dashboardSource(dash, DATASET_ID);
  return {
    start({ onDoc, onFail }) {
      base.start({
        onDoc(doc, url) {
          const p = readDashboard(dash, PRIVATE_DATASET_ID);
          onDoc(p.ok ? mergePrivate(doc, p.doc) : doc, url);
        },
        onFail
      });
    }
  };
}

export const EXPORTS = Object.assign({}, PUBLIC, { readDashboard, dashboardSource, privateSource, DATASET_ID, PRIVATE_DATASET_ID,
  GROUPS, makeExt, attentionRows, attentionGroups, capUse, routineHealth, snapshotMs, staleHours, mergePrivate, rowsOf, some, useVoice });

/* Start the dashboard, given its `dash` runtime. */
export function startDashboard(dash) {
  useVoice('you');
  registerLoaders(dash);
  const ext = makeExt(dash);
  boot(privateSource(dash), {
    groups: GROUPS, home: 'needs', rootId: 'ex-app', tipId: 'ex-tip', ext: () => ext,
    onRoute: (hash) => { if (typeof dash.setLink === 'function') dash.setLink(hash); }
  });
}

if (typeof globalThis.dash !== 'undefined' && typeof document !== 'undefined' && typeof globalThis.module === 'undefined') {
  startDashboard(globalThis.dash);
}
if (typeof globalThis.module !== 'undefined') globalThis.module.exports = EXPORTS;
