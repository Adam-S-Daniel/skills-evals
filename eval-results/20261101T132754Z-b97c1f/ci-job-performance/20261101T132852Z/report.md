# Eval report: ci-job-performance

- Timestamp: 20261101T132852Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T132754Z-b97c1f; started 2026-11-01T13:28:52Z, ended 2026-11-01T13:30:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 5.4 (5.4 to 5.4, 1 judged) | 0.1178 / 0.1178 |
| without_skill | 1 | 0 | 6/7 | 5.6 (5.6 to 5.6, 1 judged) | 0.1014 / 0.1014 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1178 / 0.1178 | 0.1014 / 0.1014 | +0.0165 | +0.0165 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 22267 / 22267 | 26827 / 26827 | -4560 | -4560 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1992 / 1992 | 2241 / 2241 | -249 | -249 |
| cache_creation_input_tokens | 19474 / 19474 | 15042 / 15042 | +4432 | +4432 |
| cache_read_input_tokens | 198667 / 198667 | 186512 / 186512 | +12155 | +12155 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 1/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
