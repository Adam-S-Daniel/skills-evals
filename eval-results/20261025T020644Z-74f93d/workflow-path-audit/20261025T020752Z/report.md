# Eval report: workflow-path-audit

- Timestamp: 20261025T020752Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T020644Z-74f93d; started 2026-10-25T02:07:52Z, ended 2026-10-25T02:22:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.13, seven_day 0.37 to 0.38, from 10 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.5925 / 1.7774 |
| without_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.6765 / 2.0296 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5925 / 0.5208 | 0.6765 / 0.6660 | -0.0841 | -0.1452 |
| num_turns | 13 / 12 | 10.3 / 10 | +2.7 | +2 |
| duration_ms | 122307.7 / 121719 | 174818.7 / 163457 | -52511 | -41738 |
| input_tokens | 24 / 22 | 20 / 20 | +4 | +2 |
| output_tokens | 8661 / 8682 | 12104.3 / 12476 | -3443.3 | -3794 |
| cache_creation_input_tokens | 33446.7 / 29972 | 29572.3 / 29179 | +3874.3 | +793 |
| cache_read_input_tokens | 537933.3 / 493234 | 418532.3 / 425114 | +119401 | +68120 |
| tool_errors | 0.7 / 0 | 1.7 / 2 | -1 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 2/3 |
| lockfile-change-routes-to-installers | 3/3 | 2/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 2/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 2/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
