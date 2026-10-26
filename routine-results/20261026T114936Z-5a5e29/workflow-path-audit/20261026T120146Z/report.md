# Eval report: workflow-path-audit

- Timestamp: 20261026T120146Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T114936Z-5a5e29; started 2026-10-26T12:01:46Z, ended 2026-10-26T12:14:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.21 to 0.24, seven_day 0.61 to 0.62, from 10 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.5353 / 1.6059 |
| without_skill | 3 | 0 | 4.7/8 | skipped (objective-decided) | 0.6119 / 1.8357 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5353 / 0.5431 | 0.6119 / 0.6046 | -0.0766 | -0.0614 |
| num_turns | 9 / 9 | 11.3 / 12 | -2.3 | -3 |
| duration_ms | 109007.7 / 108582 | 133132 / 130096 | -24124.3 | -21514 |
| input_tokens | 16 / 16 | 22.7 / 24 | -6.7 | -8 |
| output_tokens | 7376.7 / 7078 | 10221.7 / 9787 | -2845 | -2709 |
| cache_creation_input_tokens | 31397 / 28129 | 27032.3 / 27056 | +4364.7 | +1073 |
| cache_read_input_tokens | 326947.7 / 316141 | 472080 / 498418 | -145132.3 | -182277 |
| tool_errors | 0.7 / 0 | 2.7 / 3 | -2 | -3 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 1/3 |
| source-change-routes-correctly | 3/3 | 1/3 |
| lockfile-change-routes-to-installers | 3/3 | 1/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 1/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 1/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
