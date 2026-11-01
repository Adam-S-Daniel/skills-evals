# Eval report: ci-job-performance

- Timestamp: 20261101T124323Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T124230Z-f0d0db; started 2026-11-01T12:43:23Z, ended 2026-11-01T12:44:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 4 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 5.8 (5.8 to 5.8, 1 judged) | 0.1250 / 0.1250 |
| without_skill | 1 | 0 | 6/7 | 5.4 (5.4 to 5.4, 1 judged) | 0.1034 / 0.1034 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1250 / 0.1250 | 0.1034 / 0.1034 | +0.0215 | +0.0215 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 23042 / 23042 | 24504 / 24504 | -1462 | -1462 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2163 / 2163 | 2054 / 2054 | +109 | +109 |
| cache_creation_input_tokens | 19799 / 19799 | 15991 / 15991 | +3808 | +3808 |
| cache_read_input_tokens | 239984 / 239984 | 187796 / 187796 | +52188 | +52188 |
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
