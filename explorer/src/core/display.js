/* The pages' display settings, read from explorer/display.json: the one place
   they are set. build.js validates the file (display-check.js) and bundles it,
   failing with a message that names the key; nothing in src defaults a value.
   The bundles of the public pages carry the time zone only, so ISSUE_REPOS is
   read by the private page alone. */
import cfg from '../../display.json' with { type: 'json' };

export const { time_zone: TIME_ZONE, issue_repos: ISSUE_REPOS } = cfg;
