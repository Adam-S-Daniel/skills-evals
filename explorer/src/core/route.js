/* Hash routes, the same in both builds: #/summary, #/needs, #/hooks,
   #/hooks/<check>, #/skills, #/skills/<name>, #/guidance, #/guidance/<id>,
   #/removed, #/method, #/loop, #/impact, #/ops. */

/* Each top-level group and the routes it holds. `needs` exists only in the
   private build; the public entry leaves it out of its group list. */
export const GROUPS = {
  summary: ['summary'],
  needs: ['needs'],
  hooks: ['hooks', 'skills', 'guidance', 'removed', 'method'],
  loop: ['loop'],
  impact: ['impact'],
  ops: ['ops']
};
/* The project dashboard's tab names before PR4. */
export const LEGACY = { overview: 'needs', loop: 'loop', impact: 'impact', costbenefit: 'impact', evals: 'skills',
  cleanup: 'ops', work: 'ops', routines: 'ops', console: 'ops', decisions: 'ops' };
export const SUBJECT_ROUTES = ['hooks', 'skills', 'guidance'];

export function groupOf(name) {
  for (const g of Object.keys(GROUPS)) if (GROUPS[g].includes(name)) return g;
  return 'summary';
}

/* { name, id } from location.hash and location.search; anything unknown, or a
   group this build does not have, is the summary. Today's ?subject=guidance
   with no hash opens #/guidance. */
export function parseRoute(hash, search, groups) {
  const have = groups || Object.keys(GROUPS);
  const raw = String(hash || '');
  // The dashboard's old tab links (#loop, #evals, ...) open their new home.
  if (/^#[a-z]+$/.test(raw) && Object.prototype.hasOwnProperty.call(LEGACY, raw.slice(1))) {
    const to = LEGACY[raw.slice(1)];
    return have.includes(groupOf(to)) ? { name: to, id: null } : { name: 'summary', id: null };
  }
  const m = /^#\/([a-z]+)(?:\/(.+))?$/.exec(raw);
  if (!m) {
    const q = new URLSearchParams(search || '');
    if (q.get('subject') === 'guidance') return { name: 'guidance', id: null };
    return { name: 'summary', id: null };
  }
  const name = m[1];
  const g = groupOf(name);
  if (!GROUPS[g].includes(name) || !have.includes(g)) return { name: 'summary', id: null };
  let id = null;
  if (m[2] && SUBJECT_ROUTES.includes(name)) {
    try { id = decodeURIComponent(m[2]); } catch (e) { id = null; }
  }
  return { name, id };
}

export function hashFor(name, id) {
  return '#/' + name + (id ? '/' + encodeURIComponent(id) : '');
}
