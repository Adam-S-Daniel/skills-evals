# Eval report: workflow-path-audit

- Timestamp: 20261026T092152Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T092030Z-007e75; started 2026-10-26T09:21:52Z, ended 2026-10-26T09:38:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.03 to 0.07, seven_day 0.58 to 0.58, from 10 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.6009 / 1.8026 |
| without_skill | 3 | 0 | 6.3/8 | skipped (objective-decided) | 0.7212 / 2.1635 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6009 / 0.5925 | 0.7212 / 0.7074 | -0.1203 | -0.1149 |
| num_turns | 11.3 / 12 | 13 / 14 | -1.7 | -2 |
| duration_ms | 142849.3 / 141479 | 189229.7 / 182296 | -46380.3 | -40817 |
| input_tokens | 20.7 / 22 | 26 / 28 | -5.3 | -6 |
| output_tokens | 9576.3 / 9420 | 12196 / 12090 | -2619.7 | -2670 |
| cache_creation_input_tokens | 34190.3 / 31796 | 30460 / 29584 | +3730.3 | +2212 |
| cache_read_input_tokens | 457258.7 / 505068 | 554679.7 / 605736 | -97421 | -100668 |
| tool_errors | 0.7 / 1 | 2.3 / 2 | -1.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 2/3 |
| source-change-routes-correctly | 3/3 | 2/3 |
| lockfile-change-routes-to-installers | 3/3 | 2/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 2/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 2/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
