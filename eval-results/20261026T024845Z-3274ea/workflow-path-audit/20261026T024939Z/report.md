# Eval report: workflow-path-audit

- Timestamp: 20261026T024939Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T024845Z-3274ea; started 2026-10-26T02:49:39Z, ended 2026-10-26T03:03:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.23 to 0, seven_day 0.53 to 0.53, from 9 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/8 | skipped (objective-decided) | 0.6477 / 1.9430 |
| without_skill | 3 | 0 | 4.7/8 | skipped (objective-decided) | 0.6075 / 1.8225 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6477 / 0.6361 | 0.6075 / 0.6129 | +0.0402 | +0.0232 |
| num_turns | 12.3 / 12 | 10 / 10 | +2.3 | +2 |
| duration_ms | 134187 / 123613 | 138743.7 / 130723 | -4556.7 | -7110 |
| input_tokens | 22.7 / 22 | 20 / 20 | +2.7 | +2 |
| output_tokens | 9593 / 8662 | 10119.3 / 10294 | -526.3 | -1632 |
| cache_creation_input_tokens | 39037 / 33964 | 26376 / 26726 | +12661 | +7238 |
| cache_read_input_tokens | 499168.7 / 466717 | 402085.3 / 402775 | +97083.3 | +63942 |
| tool_errors | 0.7 / 1 | 2 / 2 | -1.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 2/3 | 1/3 |
| source-change-routes-correctly | 2/3 | 1/3 |
| lockfile-change-routes-to-installers | 2/3 | 1/3 |
| prose-change-runs-nothing-but-the-required-check | 2/3 | 1/3 |
| required-check-always-fires-and-gates-internally | 2/3 | 1/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
