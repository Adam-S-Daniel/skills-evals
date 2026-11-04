/* The Skills / Guidance switch. */
import { STRINGS } from '../core/strings.js';
import { h } from '../core/h.js';

export function toolbar(mode, sortBy, handlers) {
  const hd = handlers || {};
  const seg = (label, opts) => h('div', { class: 'toolbar' }, h('span', { class: 'note' }, label),
    h('div', { class: 'seg', role: 'group', 'aria-label': label }, opts.map((o) =>
      h('button', { type: 'button', 'aria-pressed': o.on ? 'true' : 'false', onclick: o.fn || null }, o.text))));
  return seg(STRINGS.modeLabel, [
    { text: STRINGS.modeSkills, on: mode === 'skills', fn: hd.skills },
    { text: STRINGS.modeGuidance, on: mode === 'guidance', fn: hd.guidance }]);
}
