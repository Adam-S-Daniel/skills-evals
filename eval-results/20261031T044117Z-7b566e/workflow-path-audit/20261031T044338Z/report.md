# Eval report: workflow-path-audit

- Timestamp: 20261031T044338Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261031T044117Z-7b566e; started 2026-10-31T04:43:37Z, ended 2026-10-31T04:45:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 4 snapshots

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.314 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.9 (8.9 to 8.9, 1 judged) | 0.2343 / 0.2343 |
| without_skill | 1 | 0 | 8/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.1280 / 0.1280 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2343 / 0.2343 | 0.1280 / 0.1280 | +0.1063 | +0.1063 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 31177 / 31177 | 34414 / 34414 | -3237 | -3237 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 3176 / 3176 | 4031 / 4031 | -855 | -855 |
| cache_creation_input_tokens | 44595 / 44595 | 15817 / 15817 | +28778 | +28778 |
| cache_read_input_tokens | 241715 / 241715 | 244210 / 244210 | -2495 | -2495 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
