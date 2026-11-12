/* Hash routes, the same in both builds: #/summary, #/needs, #/changes,
   #/changes/removed, #/hooks, #/hooks/<check>, #/skills, #/skills/<name>,
   #/guidance, #/guidance/<id>, #/method, #/spend, #/activity. */

/* Each top-level group and the routes it holds. `needs` exists only in the
   private build; the public entry leaves it out of its group list. The first
   route of a group is where its tab leads. */
export const GROUPS = {
  summary: ['summary'],
  needs: ['needs'],
  changes: ['changes'],
  results: ['hooks', 'skills', 'guidance', 'method'],
  spend: ['spend'],
  activity: ['activity']
};
/* The dashboard's tab names before the six groups, as `#overview`. */
export const LEGACY = { overview: 'needs', loop: 'changes', impact: 'spend', costbenefit: 'spend', evals: 'skills',
  cleanup: 'activity', work: 'activity', routines: 'activity', console: 'activity', decisions: 'activity' };
/* Route names an older link used (`#/loop`), and where each opens now. */
export const ALIASES = { loop: { name: 'changes', id: null }, impact: { name: 'spend', id: null }, ops: { name: 'activity', id: null },
  removed: { name: 'changes', id: 'removed' } };
/* The filters the changes list takes as its id. */
export const CHANGE_FILTERS = ['removed'];
export const SUBJECT_ROUTES = ['hooks', 'skills', 'guidance'];

export function groupOf(name) {
  for (const g of Object.keys(GROUPS)) if (GROUPS[g].includes(name)) return g;
  return 'summary';
}

/* { name, id } from location.hash and location.search; anything unknown, or a
   group this build does not have, is the summary. Today's ?subject=guidance
   with no hash opens #/guidance. `home` is the route an empty address opens
   (the private build opens Needs you); unset, it is the summary. */
export function parseRoute(hash, search, groups, home) {
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
    if (!raw && home && have.includes(groupOf(home))) return { name: home, id: null };
    return { name: 'summary', id: null };
  }
  if (Object.prototype.hasOwnProperty.call(ALIASES, m[1]) && !m[2]) {
    const to = ALIASES[m[1]];
    return have.includes(groupOf(to.name)) ? { name: to.name, id: to.id } : { name: 'summary', id: null };
  }
  const name = m[1];
  const g = groupOf(name);
  if (!GROUPS[g].includes(name) || !have.includes(g)) return { name: 'summary', id: null };
  let id = null;
  if (m[2] && SUBJECT_ROUTES.includes(name)) {
    try { id = decodeURIComponent(m[2]); } catch (e) { id = null; }
  } else if (m[2] && name === 'changes' && CHANGE_FILTERS.includes(m[2])) id = m[2];
  return { name, id };
}

export function hashFor(name, id) {
  return '#/' + name + (id ? '/' + encodeURIComponent(id) : '');
}
