/* Which models are measured, and why. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel } from '../core/format.js';
import { h } from '../core/h.js';

/* `whyFor(model)`, when given, supplies the reason shown for a model in place
   of the document's own (the private build's per-model notes). */
export function rosterView(doc, whyFor) {
  const r = doc.roster || {};
  const arms = Array.isArray(r.arms) ? r.arms : [];
  const why = (m) => (whyFor && whyFor(m.model)) || m.reason;
  const items = arms.filter(Boolean).map((a) => h('li', null, h('strong', null, STRINGS.rosterArm + ': ' + friendlyModel(a.model)),
    why(a) ? h('div', { class: 'reason' }, clean(why(a))) : null));
  if (r.judge && r.judge.model) items.push(h('li', null, h('strong', null, STRINGS.rosterJudge + ': ' + friendlyModel(r.judge.model)),
    why(r.judge) ? h('div', { class: 'reason' }, clean(why(r.judge))) : null));
  return h('section', null, h('h2', null, STRINGS.rosterHeading), h('p', { class: 'lead' }, STRINGS.rosterIntro),
    items.length ? h('ul', { class: 'plain' }, items) : h('p', null, STRINGS.rosterEmpty));
}
