# Eval report: workflow-path-audit

- Timestamp: 20261026T020304Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T020118Z-ae5346; started 2026-10-26T02:03:04Z, ended 2026-10-26T02:07:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.19 to 0.2, seven_day 0.52 to 0.52, from 7 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | 8.9 (8.9 to 8.9, 3 judged) | 0.1475 / 0.4425 |
| without_skill | 3 | 0 | 8/8 | 8.9 (8.9 to 8.9, 3 judged) | 0.1172 / 0.3515 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1475 / 0.1401 | 0.1172 / 0.1135 | +0.0303 | +0.0266 |
| num_turns | 7.7 / 8 | 6.3 / 6 | +1.3 | +2 |
| duration_ms | 29872.7 / 31362 | 35090.7 / 34810 | -5218 | -3448 |
| input_tokens | 12.7 / 14 | 12.7 / 12 | 0 | +2 |
| output_tokens | 3152.7 / 3245 | 3393.3 / 3303 | -240.7 | -58 |
| cache_creation_input_tokens | 23115.3 / 20228 | 15319.3 / 15257 | +7796 | +4971 |
| cache_read_input_tokens | 234819 / 265905 | 219418.3 / 206189 | +15400.7 | +59716 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 3/3 |
| lockfile-change-routes-to-installers | 3/3 | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 3/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
