/* Browser start-up, shared by every entry: state, rendering, the tooltip.
   Where the document comes from is the adapter's business: `source.start`
   calls `onDoc(doc, url)` with a valid document (as often as it changes) or
   `onFail(result)` with a loadData-shaped failure. */
import { STRINGS } from './core/strings.js';
import { modeFromSearch, searchForMode } from './core/format.js';
import { toDom } from './core/h.js';
import { buildPage } from './views/page.js';
import { buildFailure } from './views/failure.js';
import { DEFAULT_DATA_URL } from './adapters/web.js';

export function boot(source) {
  const app = document.getElementById('app');
  const tip = document.getElementById('tip');
  const state = { mode: modeFromSearch(location.search), sortBy: 'next', doc: null, url: DEFAULT_DATA_URL, notice: null };
  try { const s = localStorage.getItem('explorer-sort'); if (s === 'size' || s === 'value' || s === 'next') state.sortBy = s; } catch (e) { /* storage unavailable */ }

  function mount(node) {
    while (app.firstChild) app.removeChild(app.firstChild);
    app.appendChild(toDom(node, document));
    document.title = STRINGS.title;
  }
  function setMode(m) {
    state.mode = m;
    try { history.replaceState(null, '', location.pathname + searchForMode(location.search, m) + location.hash); } catch (e) { /* sandboxed frame */ }
    render();
  }
  function setSort(s) {
    state.sortBy = s;
    try { localStorage.setItem('explorer-sort', s); } catch (e) { /* storage unavailable */ }
    render();
  }
  function render() {
    mount(buildPage(state.doc, state.mode, { sortBy: state.sortBy, url: state.url, notice: state.notice, handlers: {
      skills: () => setMode('skills'), guidance: () => setMode('guidance'),
      sortNext: () => setSort('next'), sortValue: () => setSort('value'), sortSize: () => setSort('size') } }));
  }
  function showTip(target) {
    const text = target && target.getAttribute && target.getAttribute('data-tip');
    if (!text) { tip.hidden = true; return; }
    tip.textContent = text;
    tip.hidden = false;
    const r = target.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = Math.min(window.innerWidth - tw - 8, Math.max(8, r.left + r.width / 2 - tw / 2));
    let top;
    if (target.getAttribute('data-tip-pos') === 'below') {
      top = r.bottom + 8;
      if (top + th > window.innerHeight - 8) top = r.top - th - 8;
    } else {
      top = r.top - th - 8;
      if (top < 8) top = r.bottom + 8;
    }
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  app.addEventListener('pointerover', (e) => showTip(e.target.closest ? e.target.closest('[data-tip]') : null));
  app.addEventListener('pointerout', () => { tip.hidden = true; });
  app.addEventListener('focusin', (e) => {
    let kb = true;
    try { kb = e.target.matches(':focus-visible'); } catch (err) { /* old browser */ }
    if (kb) showTip(e.target);
  });
  app.addEventListener('pointerdown', () => { tip.hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') tip.hidden = true; });
  app.addEventListener('focusout', () => { tip.hidden = true; });
  window.addEventListener('scroll', () => { tip.hidden = true; }, { passive: true });

  source.start({
    onDoc(doc, url) {
      state.doc = doc;
      if (url) state.url = url;
      try { render(); } catch (e) {
        mount(buildFailure({ kind: 'parse', url: state.url }, state.mode));
      }
    },
    onFail(result) { mount(buildFailure(result, state.mode)); }
  });
}

/* True in a browser page, false in Node or the test sandbox. */
export function inBrowser() {
  return typeof window !== 'undefined' && typeof document !== 'undefined' && typeof globalThis.module === 'undefined';
}
