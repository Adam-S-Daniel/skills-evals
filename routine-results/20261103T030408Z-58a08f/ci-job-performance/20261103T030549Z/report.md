# Eval report: ci-job-performance

- Timestamp: 20261103T030549Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T030408Z-58a08f; started 2026-11-03T03:05:49Z, ended 2026-11-03T03:08:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.31 to 0.31, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.19 over 2 call(s); agent $1.19, judge $0.00, guard $0.00; last agent call $0.57

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.6201 / 0.6201 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.5732 / 0.5732 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6201 / 0.6201 | 0.5732 / 0.5732 | +0.0469 | +0.0469 |
| num_turns | 14 / 14 | 12 / 12 | +2 | +2 |
| duration_ms | 60354 / 60354 | 98374 / 98374 | -38020 | -38020 |
| input_tokens | 24 / 24 | 26 / 26 | -2 | -2 |
| output_tokens | 5295 / 5295 | 6325 / 6325 | -1030 | -1030 |
| cache_creation_input_tokens | 51232 / 51232 | 41359 / 41359 | +9873 | +9873 |
| cache_read_input_tokens | 521218 / 521218 | 546109 / 546109 | -24891 | -24891 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 1/1 |
| browser-install-runs-on-every-leg | 1/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
