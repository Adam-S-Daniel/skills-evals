/* Sections and skills the evals removed (#557). */
import { STRINGS } from '../core/strings.js';
import { clean } from '../core/format.js';
import { h, link } from '../core/h.js';

/* Sections the evals removed (#557), with the date and a link to the
   removal pull request, whose Revert button restores the section. */
export function removedView(doc) {
  const removed = (doc.guidance && Array.isArray(doc.guidance.removed) ? doc.guidance.removed : [])
    .filter((r) => r && typeof r.id === 'string' && typeof r.date === 'string');
  if (!removed.length) return null;
  return h('section', null, h('h2', null, STRINGS.removedHeading), h('p', { class: 'note' }, STRINGS.removedNote),
    h('ul', null, removed.map((r) => h('li', null, h('strong', null, clean(r.id)), ' ', clean(r.date), ' ',
      link(r.reverse_url, STRINGS.removedLink)))));
}

/* Skills the evals removed (#557), with the date and a link to the removal
   pull request, whose Revert button restores the skill. */
export function removedSkillsView(doc) {
  const removed = (Array.isArray(doc.removed_skills) ? doc.removed_skills : [])
    .filter((r) => r && typeof r.name === 'string' && typeof r.date === 'string');
  if (!removed.length) return null;
  return h('section', null, h('h2', null, STRINGS.removedSkillsHeading), h('p', { class: 'note' }, STRINGS.removedSkillsNote),
    h('ul', null, removed.map((r) => h('li', null, h('strong', null, clean(r.name)), ' ', clean(r.date), ' ',
      link(r.reverse_url, STRINGS.removedLink)))));
}
