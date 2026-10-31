# Eval report: workflow-path-audit

- Timestamp: 20261031T161455Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261031T161316Z-993cb6; started 2026-10-31T16:14:55Z, ended 2026-10-31T16:16:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.9 (8.9 to 8.9, 1 judged) | 0.2393 / 0.2393 |
| without_skill | 1 | 0 | 8/8 | 8.7 (8.7 to 8.7, 1 judged) | 0.1149 / 0.1149 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2393 / 0.2393 | 0.1149 / 0.1149 | +0.1244 | +0.1244 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 35460 / 35460 | 37871 / 37871 | -2411 | -2411 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 3479 / 3479 | 3470 / 3470 | +9 | +9 |
| cache_creation_input_tokens | 45083 / 45083 | 14886 / 14886 | +30197 | +30197 |
| cache_read_input_tokens | 241846 / 241846 | 206517 / 206517 | +35329 | +35329 |
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
