# Eval report: workflow-path-audit

- Timestamp: 20261020T205241Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261020T205134Z-ee923a; started 2026-10-20T20:52:41Z, ended 2026-10-20T20:56:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.1, seven_day 0.1 to 0.1, from 8 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.304 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1658 / 0.4975 |
| without_skill | 3 | 0 | 7.7/8 | skipped (objective-decided) | 0.1527 / 0.4581 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1658 / 0.1628 | 0.1527 / 0.1503 | +0.0132 | +0.0125 |
| num_turns | 6.7 / 6 | 5 / 5 | +1.7 | +1 |
| duration_ms | 29288.7 / 27710 | 36591.3 / 36620 | -7302.7 | -8910 |
| input_tokens | 9.3 / 8 | 10 / 10 | -0.7 | -2 |
| output_tokens | 2964 / 2894 | 3437 / 3407 | -473 | -513 |
| cache_creation_input_tokens | 30271.7 / 30358 | 25832 / 25600 | +4439.7 | +4758 |
| cache_read_input_tokens | 150986 / 123533 | 149739 / 150263 | +1247 | -26730 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 3/3 |
| lockfile-change-routes-to-installers | 3/3 | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 3/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 2/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
