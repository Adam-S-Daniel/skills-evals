/* The page shown when the results cannot be shown. */
import { STRINGS } from '../core/strings.js';
import { h } from '../core/h.js';
import { DEFAULT_DATA_URL } from '../adapters/web.js';

export function buildFailure(result, mode) {
  let msg;
  if (result.kind === 'schema') msg = STRINGS.failSchema(result.got);
  else if (result.kind === 'parse') msg = STRINGS.failParse;
  else if (result.kind === 'badurl') msg = STRINGS.failBadUrl;
  else msg = STRINGS.failFetch;
  return h('div', null,
    h('h1', null, STRINGS.title),
    h('div', { class: 'panel failure', role: 'alert' },
      h('h2', { style: 'margin-top:0' }, STRINGS.failHeading),
      h('p', null, msg),
      h('p', null, STRINGS.failFile(result.url || DEFAULT_DATA_URL)),
      h('p', null, STRINGS.failWhat)));
}
