/* Tap-for-definition: a real button that opens one definition box next to it.
   The box is a non-modal dialog inserted right after its button, so the
   keyboard order stays natural; Escape, the Close button or a click elsewhere
   closes it, and focus returns to the button. */
import { h } from './h.js';
import { TERMS } from './glosses.js';
import { STRINGS } from './strings.js';

export const DEF_ID = 'ex-def';
let open = null; // { btn, box }

function place(btn, box) {
  const r = btn.getBoundingClientRect();
  const vw = window.innerWidth, vh = window.innerHeight;
  const w = Math.min(box.offsetWidth, vw - 16), hh = box.offsetHeight;
  const left = Math.min(vw - w - 8, Math.max(8, r.left));
  let top = r.bottom + 6;
  if (top + hh > vh - 8 && r.top - hh - 6 >= 8) top = r.top - hh - 6;
  top = Math.max(8, top);
  box.style.left = left + 'px';
  box.style.top = top + 'px';
  // A size container (the dashboard page's #ex-root) anchors a fixed box to
  // itself, not the viewport: shift by however far it actually landed off.
  const at = box.getBoundingClientRect();
  if (at.left !== left || at.top !== top) {
    box.style.left = (2 * left - at.left) + 'px';
    box.style.top = (2 * top - at.top) + 'px';
  }
}

export function closeDef(returnFocus) {
  if (!open) return;
  const { btn, box } = open;
  open = null;
  if (box.parentNode) box.parentNode.removeChild(box);
  btn.setAttribute('aria-expanded', 'false');
  if (returnFocus && btn.isConnected) btn.focus();
}

function toggle(e) {
  const btn = e.currentTarget;
  e.stopPropagation();
  if (open && open.btn === btn) { closeDef(true); return; }
  closeDef(false);
  const doc = btn.ownerDocument;
  const title = btn.getAttribute('data-def-title') || btn.textContent;
  const box = doc.createElement('span');
  box.id = DEF_ID;
  box.className = 'defbox';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', title);
  box.tabIndex = -1;
  const head = doc.createElement('strong');
  head.className = 'defbox-title';
  head.textContent = title;
  const body = doc.createElement('span');
  body.className = 'defbox-text';
  body.textContent = btn.getAttribute('data-def');
  const close = doc.createElement('button');
  close.type = 'button';
  close.className = 'defbox-close';
  close.textContent = STRINGS.defClose;
  close.addEventListener('click', (ev) => { ev.stopPropagation(); closeDef(true); });
  box.appendChild(head); box.appendChild(body); box.appendChild(close);
  btn.parentNode.insertBefore(box, btn.nextSibling);
  btn.setAttribute('aria-expanded', 'true');
  open = { btn, box };
  place(btn, box);
  box.focus({ preventScroll: true });
}

/* A button that opens `text` as its definition. `title` heads the box
   (default: the label). */
export function term(label, text, opts) {
  const o = opts || {};
  return h('button', { type: 'button', class: 'term' + (o.cls ? ' ' + o.cls : ''), 'aria-expanded': 'false', 'aria-controls': DEF_ID,
    'aria-haspopup': 'dialog', 'data-def': text, 'data-def-title': o.title || (typeof label === 'string' ? label : ''),
    'aria-label': o.aria || null, onclick: toggle }, label);
}

/* The glossary term `key` (core/glosses.js TERMS), shown as `label` or its
   own word. An unknown key is plain text, never a dead button. */
export function defn(key, label) {
  const t = Object.prototype.hasOwnProperty.call(TERMS, key) ? TERMS[key] : null;
  if (!t) return label || key;
  return term(label || t.label, t.text, { title: t.label });
}

/* What the data says about a subject or fixture, set once per render by
   renderRoute from the document. */
const known = { skills: new Map(), sections: new Map(), fixtures: new Map() };
export function indexDoc(doc, purposeOf, glossOf) {
  known.skills.clear(); known.sections.clear(); known.fixtures.clear();
  for (const s of Array.isArray(doc.skills) ? doc.skills : []) if (s && s.name) known.skills.set(String(s.name), purposeOf(s.description));
  const secs = doc.guidance && Array.isArray(doc.guidance.sections) ? doc.guidance.sections : [];
  for (const s of secs) if (s && s.id) known.sections.set(String(s.id), { heading: s.heading || s.id, text: glossOf(s.id) });
  const fq = doc.fixture_queue && Array.isArray(doc.fixture_queue.fixtures) ? doc.fixture_queue.fixtures : [];
  for (const f of fq) {
    if (f && typeof f.path === 'string') known.fixtures.set(f.path.split('/').pop(), { origin: f.origin_kind || null, runs: Number.isInteger(f.runs) ? f.runs : null, subject: f.subject || null });
  }
}

/* A skill's name as a definition button; its text is the first sentence of
   its SKILL.md description, or a note that none was recorded. */
export function skillTerm(name, label) {
  const d = known.skills.get(String(name));
  return term(label || name, d || STRINGS.noDescription, { title: String(name), cls: 'name' });
}
export function sectionTerm(id, label) {
  const k = known.sections.get(String(id));
  return term(label || (k && k.heading) || id, k && k.text ? k.text : STRINGS.noDescription, { title: (k && k.heading) || String(id), cls: 'name' });
}

/* A fixture's name as a definition button: what a fixture is, plus whatever
   the fixture queue recorded about this one. The data holds no task title. */
export function fixtureTerm(name, label) {
  const leaf = String(name || '').split('/').pop();
  const k = known.fixtures.get(leaf);
  const bits = [TERMS.fixture ? TERMS.fixture.text : ''];
  if (k) {
    if (k.origin) bits.push(STRINGS.fixtureOrigin(k.origin));
    if (k.runs !== null) bits.push(STRINGS.fixtureRuns(k.runs));
  }
  bits.push(STRINGS.noDescriptionFixture);
  return term(label || String(name), bits.join(' '), { title: String(name), cls: 'name' });
}

/* A sentence from the data as text and definition buttons: the first match
   of each `[pattern, key]` becomes the glossary term `key`. */
export function termify(text, pairs) {
  let parts = [String(text)];
  for (const [re, key] of pairs) {
    const next = [];
    let done = false;
    for (const p of parts) {
      const m = !done && typeof p === 'string' ? re.exec(p) : null;
      if (!m) { next.push(p); continue; }
      done = true;
      next.push(p.slice(0, m.index), defn(key, m[0]), p.slice(m.index + m[0].length));
    }
    parts = next;
  }
  return parts;
}
export const SENTENCE_TERMS = [[/\btrials?\b/, 'trial'], [/\bchecks\b/, 'check']];

let installed = false;
/* Once per page: Escape closes the box, and so does a press elsewhere. */
export function installDefs(doc) {
  if (installed) return;
  installed = true;
  doc.addEventListener('keydown', (e) => { if (e.key === 'Escape' && open) { e.stopPropagation(); closeDef(true); } }, true);
  doc.addEventListener('pointerdown', (e) => {
    if (open && !(e.target.closest && (e.target.closest('.defbox') || e.target.closest('.term')))) closeDef(false);
  });
  window.addEventListener('resize', () => { if (open) place(open.btn, open.box); });
  window.addEventListener('scroll', () => { if (open) place(open.btn, open.box); }, { passive: true });
}
