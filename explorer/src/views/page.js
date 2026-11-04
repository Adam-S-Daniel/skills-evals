/* The whole page for one document and mode. */
import { STRINGS } from '../core/strings.js';
import { parseTime, fmtDateTime } from '../core/format.js';
import { h } from '../core/h.js';
import { skillItems, sectionItems, wholeGuidance } from '../core/items.js';
import { DEFAULT_DATA_URL } from '../adapters/web.js';
import { introView } from './intro.js';
import { toolbar } from './toolbar.js';
import { wholeView } from './whole.js';
import { skillCard, sectionCard, chipSummary } from './cards.js';
import { rosterView } from './roster.js';
import { coverageView } from './coverage.js';
import { alertsView } from './alerts.js';
import { engineersView } from './engineers.js';
import { removedView, removedSkillsView } from './removed.js';
import { lessonsView } from './lessons.js';

export function buildPage(doc, mode, opts) {
  const o = opts || {};
  const refMs = parseTime(doc.generated_at);
  const newest = parseTime(doc.newest_run);
  const top = [
    h('h1', null, STRINGS.title),
    h('p', { class: 'asof' }, STRINGS.dataAsOf(fmtDateTime(refMs)), ' ', isFinite(newest) ? STRINGS.newestRun(fmtDateTime(newest)) : STRINGS.noRunsYet),
    toolbar(mode, o.sortBy, o.handlers),
    o.notice ? h('p', { class: 'panel failure' }, o.notice) : null,
    introView(mode)
  ];
  let body;
  if (mode === 'guidance') {
    const whole = wholeGuidance(doc);
    const items = sectionItems(doc, o.sortBy);
    const hd = o.handlers || {};
    body = [
      wholeView(whole, refMs),
      h('section', null, h('h2', null, STRINGS.sectionsHeading), h('p', { class: 'note' }, STRINGS.sectionsNote),
        chipSummary(items, mode),
        h('div', { class: 'toolbar' }, h('span', { class: 'note' }, STRINGS.sortLabel),
          h('div', { class: 'seg', role: 'group', 'aria-label': STRINGS.sortLabel },
            h('button', { type: 'button', 'aria-pressed': o.sortBy !== 'size' && o.sortBy !== 'value' ? 'true' : 'false', onclick: hd.sortNext || null }, STRINGS.sortNext),
            h('button', { type: 'button', 'aria-pressed': o.sortBy === 'value' ? 'true' : 'false', onclick: hd.sortValue || null }, STRINGS.sortValue),
            h('button', { type: 'button', 'aria-pressed': o.sortBy === 'size' ? 'true' : 'false', onclick: hd.sortSize || null }, STRINGS.sortSize))),
        items.length ? h('div', { class: 'cards' }, items.map((it) => sectionCard(it, refMs, doc))) : h('p', null, STRINGS.noCards)),
      lessonsView(doc, mode),
      removedView(doc)
    ];
  } else {
    const items = skillItems(doc);
    const u = doc.usage;
    body = [h('section', null, h('h2', null, STRINGS.skillsHeading), h('p', { class: 'note' }, STRINGS.skillsNote),
      u && typeof u.sessions_scanned === 'number' ? h('p', { class: 'note' }, STRINGS.usageNote(u.sessions_scanned.toLocaleString('en-US'))) : null,
      chipSummary(items, mode),
      items.length ? h('div', { class: 'cards' }, items.map((it) => skillCard(it, refMs, doc))) : h('p', null, STRINGS.noCards)),
      lessonsView(doc, mode),
      removedSkillsView(doc)];
  }
  return h('div', null, top, body, rosterView(doc), coverageView(doc, mode), alertsView(doc, mode), engineersView(doc, mode, o.url || DEFAULT_DATA_URL));
}
