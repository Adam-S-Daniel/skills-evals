/* Which models are measured, and why. */
import { STRINGS } from '../core/strings.js';
import { clean, friendlyModel } from '../core/format.js';
import { h } from '../core/h.js';

export function rosterView(doc) {
  const r = doc.roster || {};
  const arms = Array.isArray(r.arms) ? r.arms : [];
  const items = arms.filter(Boolean).map((a) => h('li', null, h('strong', null, STRINGS.rosterArm + ': ' + friendlyModel(a.model)),
    a.reason ? h('div', { class: 'reason' }, clean(a.reason)) : null));
  if (r.judge && r.judge.model) items.push(h('li', null, h('strong', null, STRINGS.rosterJudge + ': ' + friendlyModel(r.judge.model)),
    r.judge.reason ? h('div', { class: 'reason' }, clean(r.judge.reason)) : null));
  return h('section', null, h('h2', null, STRINGS.rosterHeading), h('p', { class: 'lead' }, STRINGS.rosterIntro),
    items.length ? h('ul', { class: 'plain' }, items) : h('p', null, STRINGS.rosterEmpty));
}
