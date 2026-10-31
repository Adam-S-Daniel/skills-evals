# Eval report: workflow-path-audit

- Timestamp: 20261031T185948Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261031T185821Z-a37f6c; started 2026-10-31T18:59:48Z, ended 2026-10-31T19:01:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 4 snapshots

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.2356 / 0.2356 |
| without_skill | 1 | 0 | 8/8 | 8.9 (8.9 to 8.9, 1 judged) | 0.1301 / 0.1301 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2356 / 0.2356 | 0.1301 / 0.1301 | +0.1056 | +0.1056 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 33946 / 33946 | 38675 / 38675 | -4729 | -4729 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3537 / 3537 | 4405 / 4405 | -868 | -868 |
| cache_creation_input_tokens | 44992 / 44992 | 16323 / 16323 | +28669 | +28669 |
| cache_read_input_tokens | 202651 / 202651 | 206884 / 206884 | -4233 | -4233 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 1/1 | 1/1 |
| source-change-routes-correctly | 1/1 | 1/1 |
| lockfile-change-routes-to-installers | 1/1 | 1/1 |
| prose-change-runs-nothing-but-the-required-check | 1/1 | 1/1 |
| required-check-always-fires-and-gates-internally | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
