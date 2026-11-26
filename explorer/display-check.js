/* Validates explorer/display.json, the one place the pages name the time zone
   they display and the repositories whose issues the private page lists. Pure
   (no file or network access), so build.js checks the file before it bundles
   and the tests call it with bad documents. `file` only words the messages. */
const REPO_NAME = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/(?!\.+$)[A-Za-z0-9._-]{1,100}$/;
/* An IANA name has Area/Location parts (Europe/Berlin, America/Argentina/Buenos_Aires) or is UTC; Intl alone also takes "est" and "+05:00". */
const IANA_NAME = /^(?:UTC|[A-Za-z_]+(?:\/[A-Za-z0-9_+-]+)+)$/;

export function validateDisplay(cfg, file) {
  const where = file || 'explorer/display.json';
  const fail = (key, what) => { throw new Error(where + ' key "' + key + '" ' + what); };
  if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) throw new Error(where + ' must hold a JSON object with the keys "time_zone" and "issue_repos"');
  if (typeof cfg.time_zone !== 'string' || cfg.time_zone === '') {
    fail('time_zone', 'is missing: set it to the IANA time zone the pages display, for example "Europe/Berlin"');
  }
  try {
    if (!IANA_NAME.test(cfg.time_zone)) throw new RangeError('not Area/Location');
    new Intl.DateTimeFormat('en-US', { timeZone: cfg.time_zone });
  } catch (e) {
    fail('time_zone', 'is "' + cfg.time_zone + '", which is not an IANA time zone name: set it to one such as "Europe/Berlin"');
  }
  if (!Array.isArray(cfg.issue_repos) || cfg.issue_repos.length === 0) {
    fail('issue_repos', 'is missing or empty: list the repositories whose issues, pull requests and merges the private page shows, as ["owner/repo", ...], the first being the repository holding this page\'s data');
  }
  const seen = new Set();
  for (const r of cfg.issue_repos) {
    if (typeof r !== 'string' || !REPO_NAME.test(r)) fail('issue_repos', 'holds ' + JSON.stringify(r) + ', which is not an "owner/repo" GitHub name');
    if (seen.has(r)) fail('issue_repos', 'lists "' + r + '" twice');
    seen.add(r);
  }
  return { timeZone: cfg.time_zone, issueRepos: cfg.issue_repos.slice() };
}
