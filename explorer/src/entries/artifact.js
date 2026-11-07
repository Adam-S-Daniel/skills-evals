/* The Evals Explorer as a claude.ai artifact (explorer/dist/artifact/index.html,
   published with latest.json beside it). The public entry with one change:
   build.js resolves adapters/web.js to adapters/artifact.js in this bundle,
   so the page reads the relative URL latest.json from its own origin. */
import { EXPORTS } from './shared.js';
import { webSource } from '../adapters/artifact.js';
import { boot, inBrowser } from '../app.js';

if (inBrowser()) boot(webSource((u, o) => fetch(u, o), location.search, Date.now()));
if (typeof globalThis.module !== 'undefined') globalThis.module.exports = EXPORTS;
