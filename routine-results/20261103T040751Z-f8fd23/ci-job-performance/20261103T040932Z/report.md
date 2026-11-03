# Eval report: ci-job-performance

- Timestamp: 20261103T040932Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T040751Z-f8fd23; started 2026-11-03T04:09:32Z, ended 2026-11-03T04:10:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: browser-cache (n=1)

- Prompt: Our e2e workflow got slower after we added a Playwright browser cache last week. Use the workflow's recent runs (gh is authenticated for example-org/example-repo) to find out what the cache actually does for each browser, and fix .github/workflows/e2e.yml accordingly. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1817 / 0.1817 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1083 / 0.1083 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1817 / 0.1817 | 0.1083 / 0.1083 | +0.0734 | +0.0734 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 38010 / 38010 | 27595 / 27595 | +10415 | +10415 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2229 / 2229 | 2279 / 2279 | -50 | -50 |
| cache_creation_input_tokens | 34289 / 34289 | 16969 / 16969 | +17320 | +17320 |
| cache_read_input_tokens | 222419 / 222419 | 176618 / 176618 | +45801 | +45801 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-timings-read-without-writes | 1/1 | 1/1 |
| firefox-leg-restores-no-browser-cache | 1/1 | 1/1 |
| chromium-leg-still-restores-the-cache | 1/1 | 1/1 |
| browser-cache-keyed-on-the-lockfile | 1/1 | 0/1 |
| browser-install-runs-on-every-leg | 0/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
