/* Browser start-up, shared by every entry: the top bar, the router, state,
   rendering and the tooltip. Where the document comes from is the adapter's
   business: `source.start` calls `onDoc(doc, url)` with a valid document (as
   often as it changes) or `onFail(result)` with a loadData-shaped failure. */
import { STRINGS } from './core/strings.js';
import { toDom, h } from './core/h.js';
import { parseRoute, hashFor, groupOf } from './core/route.js';
import { renderRoute } from './views/page.js';
import { buildFailure } from './views/failure.js';
import { DEFAULT_DATA_URL } from './adapters/web.js';
import { installDefs } from './core/terms.js';

/* opts: { groups (the top-level groups this build has, in order), ext
   (state -> the private overlays, or null), rootId, tipId, onRoute(hash) }. */
export function boot(source, opts) {
  const o = opts || {};
  const groups = o.groups || ['summary', 'hooks', 'loop', 'impact', 'ops'];
  const root = document.getElementById(o.rootId || 'app');
  const tip = document.getElementById(o.tipId || 'tip');
  const state = { route: parseRoute(location.hash, location.search, groups), sortBy: 'next', doc: null, url: DEFAULT_DATA_URL,
    notice: null, search: { text: '', registry: '', verdict: '', model: '', stakes: '' } };
  try { const s = localStorage.getItem('explorer-sort'); if (s === 'size' || s === 'value' || s === 'next') state.sortBy = s; } catch (e) { /* storage unavailable */ }

  // The top bar is built once, so the search box keeps its focus while the
  // content below it re-renders on every keystroke.
  const top = toDom(h('header', { class: 'topbar' },
    h('div', { class: 'bar' },
      h('a', { class: 'brand', href: hashFor('summary') }, STRINGS.title),
      h('button', { type: 'button', class: 'menu', 'aria-expanded': 'false', 'aria-controls': 'ex-drawer', onclick: () => toggleMenu() }, STRINGS.menu),
      h('div', { class: 'drawer', id: 'ex-drawer' },
        h('nav', { class: 'groups', 'aria-label': STRINGS.navLabel }, groups.map((g) =>
          h('a', { id: 'tab-' + g, href: hashFor(g === 'hooks' ? 'hooks' : g), class: 'group' }, STRINGS.groups[g]))),
        h('input', { type: 'search', class: 'search', placeholder: STRINGS.searchPlaceholder, 'aria-label': STRINGS.searchLabel,
          oninput: (e) => { state.search.text = e.currentTarget.value; renderContent(); } })))), document);
  const content = document.createElement('div');
  content.className = 'content';
  while (root.firstChild) {
    // keep the template's loading line until the first render
    content.appendChild(root.firstChild);
  }
  root.appendChild(top);
  root.appendChild(content);
  const searchBox = top.querySelector('input.search');

  function toggleMenu(force) {
    const open = force === undefined ? !top.classList.contains('open') : force;
    top.classList.toggle('open', open);
    top.querySelector('.menu').setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function markNav() {
    const g = groupOf(state.route.name);
    top.querySelectorAll('a.group').forEach((a) => {
      if (a.id === 'tab-' + g) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
  }
  // True for the next render only: a new route or the first document, so a
  // view rises in once and never on a keystroke, a sort or a data refresh.
  let entering = true;
  function mount(node) {
    content.classList.toggle('enter', entering);
    entering = false;
    while (content.firstChild) content.removeChild(content.firstChild);
    content.appendChild(toDom(node, document));
    document.title = STRINGS.title;
  }
  function setSort(s) {
    state.sortBy = s;
    try { localStorage.setItem('explorer-sort', s); } catch (e) { /* storage unavailable */ }
    renderContent();
  }
  function clearSearch() {
    state.search = { text: '', registry: '', verdict: '', model: '', stakes: '' };
    searchBox.value = '';
    renderContent();
  }
  function renderContent() {
    markNav();
    if (!state.doc) return;
    try {
      mount(renderRoute(state.doc, state.route, { sortBy: state.sortBy, url: state.url, notice: state.notice,
        ext: o.ext ? o.ext(state) : null, search: state.search,
        onFilter: (k, v) => { state.search[k] = v; renderContent(); }, onClear: clearSearch,
        handlers: { sortNext: () => setSort('next'), sortValue: () => setSort('value'), sortSize: () => setSort('size') } }));
    } catch (e) {
      mount(buildFailure({ kind: 'parse', url: state.url }));
    }
  }
  window.addEventListener('hashchange', () => {
    state.route = parseRoute(location.hash, location.search, groups);
    state.search = { text: '', registry: '', verdict: '', model: '', stakes: '' };
    searchBox.value = '';
    toggleMenu(false);
    if (o.onRoute) { try { o.onRoute(location.hash); } catch (e) { /* host without deep links */ } }
    entering = true;
    renderContent();
    try { window.scrollTo(0, 0); } catch (e) { /* no window scroll */ }
  });

  function showTip(target) {
    const text = target && target.getAttribute && target.getAttribute('data-tip');
    if (!text) { tip.hidden = true; return; }
    tip.textContent = text;
    tip.hidden = false;
    const r = target.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    const left = Math.min(window.innerWidth - tw - 8, Math.max(8, r.left + r.width / 2 - tw / 2));
    let topPx;
    if (target.getAttribute('data-tip-pos') === 'below') {
      topPx = r.bottom + 8;
      if (topPx + th > window.innerHeight - 8) topPx = r.top - th - 8;
    } else {
      topPx = r.top - th - 8;
      if (topPx < 8) topPx = r.bottom + 8;
    }
    tip.style.left = left + 'px';
    tip.style.top = topPx + 'px';
  }
  root.addEventListener('pointerover', (e) => showTip(e.target.closest ? e.target.closest('[data-tip]') : null));
  root.addEventListener('pointerout', () => { tip.hidden = true; });
  root.addEventListener('focusin', (e) => {
    let kb = true;
    try { kb = e.target.matches(':focus-visible'); } catch (err) { /* old browser */ }
    if (kb) showTip(e.target);
  });
  root.addEventListener('pointerdown', () => { tip.hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { tip.hidden = true; toggleMenu(false); } });
  root.addEventListener('focusout', () => { tip.hidden = true; });
  window.addEventListener('scroll', () => { tip.hidden = true; }, { passive: true });

  installDefs(document);
  markNav();
  source.start({
    onDoc(doc, url) {
      state.doc = doc;
      if (url) state.url = url;
      renderContent();
    },
    onFail(result) { mount(buildFailure(result)); }
  });
}

/* True in a browser page, false in Node or the test sandbox. */
export function inBrowser() {
  return typeof window !== 'undefined' && typeof document !== 'undefined' && typeof globalThis.module === 'undefined';
}
