/* The public Evals Explorer (tool/index.html, published to
   adamdaniel.ai/tools/evals/). Imports only public views and the web
   adapter; explorer/test/run.js holds the built bundle to that. */
import { EXPORTS } from './shared.js';
import { webSource } from '../adapters/web.js';
import { boot, inBrowser } from '../app.js';

if (inBrowser()) boot(webSource((u, o) => fetch(u, o), location.search, Date.now()));
/* tool/test/run.js runs the built page in a Node sandbox that defines `module`. */
if (typeof globalThis.module !== 'undefined') globalThis.module.exports = EXPORTS;
