# Eval report: ci-job-performance

- Timestamp: 20261101T185649Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T185553Z-c91488; started 2026-11-01T18:56:49Z, ended 2026-11-01T18:57:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.91 to 0.91, from 2 snapshots

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1171 / 0.1171 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1211 / 0.1211 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1171 / 0.1171 | 0.1211 / 0.1211 | -0.0039 | -0.0039 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 24331 / 24331 | 30735 / 30735 | -6404 | -6404 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2044 / 2044 | 1899 / 1899 | +145 | +145 |
| cache_creation_input_tokens | 19171 / 19171 | 20524 / 20524 | -1353 | -1353 |
| cache_read_input_tokens | 198450 / 198450 | 198354 / 198354 | +96 | +96 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 0/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
