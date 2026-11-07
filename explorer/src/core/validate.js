/* The one schema check every adapter applies to the document it gets. */
import { SCHEMA_VERSION } from './rules.js';
import { STRINGS } from './strings.js';
import { clean } from './format.js';

export function validateDoc(doc) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return { ok: false, kind: 'parse' };
  if (doc.schema_version !== SCHEMA_VERSION) {
    const got = (typeof doc.schema_version === 'number' || typeof doc.schema_version === 'string')
      ? clean(doc.schema_version) : STRINGS.unknown;
    return { ok: false, kind: 'schema', got: got };
  }
  return { ok: true };
}
