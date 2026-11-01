# Eval report: ci-job-performance

- Timestamp: 20261101T152743Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T152649Z-74d750; started 2026-11-01T15:27:43Z, ended 2026-11-01T15:29:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 4 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 5.4 (5.4 to 5.4, 1 judged) | 0.1548 / 0.1548 |
| without_skill | 1 | 0 | 6/7 | 5.2 (5.2 to 5.2, 1 judged) | 0.1028 / 0.1028 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1548 / 0.1548 | 0.1028 / 0.1028 | +0.0520 | +0.0520 |
| num_turns | 11 / 11 | 5 / 5 | +6 | +6 |
| duration_ms | 48189 / 48189 | 26167 / 26167 | +22022 | +22022 |
| input_tokens | 20 / 20 | 10 / 10 | +10 | +10 |
| output_tokens | 3153 / 3153 | 2280 / 2280 | +873 | +873 |
| cache_creation_input_tokens | 21295 / 21295 | 15288 / 15288 | +6007 | +6007 |
| cache_read_input_tokens | 378769 / 378769 | 186723 / 186723 | +192046 | +192046 |
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
