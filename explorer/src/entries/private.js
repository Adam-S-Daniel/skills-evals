/* The private project dashboard's explorer views (dashboard/page, a
   claude.ai Dashboard artifact). For now the same views as the public page,
   read through the dashboard adapter; the next change adds the private
   panels and wires this into the dashboard. Never imported by public.js. */
import { EXPORTS as PUBLIC } from './shared.js';
import { readDashboard, dashboardSource, DATASET_ID } from '../adapters/dashboard.js';
import { boot } from '../app.js';

/* Placeholder: the private-only panels, filled by the next change. */
export const PRIVATE_VIEWS = [];

export const EXPORTS = Object.assign({}, PUBLIC, { readDashboard, dashboardSource, DATASET_ID, PRIVATE_VIEWS });

/* Start the explorer inside a Dashboard page, given its `dash` runtime. */
export function startDashboard(dash) {
  boot(dashboardSource(dash));
}
