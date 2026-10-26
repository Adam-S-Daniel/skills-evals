# Eval report: workflow-path-audit

- Timestamp: 20261026T145344Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145343Z-40dd72; started 2026-10-26T14:53:44Z, ended 2026-10-26T14:59:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.65 to 0.69, seven_day 0.79 to 0.8, from 10 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | 8.9 (8.9 to 8.9, 3 judged) | 0.1460 / 0.4379 |
| without_skill | 3 | 0 | 8/8 | 8.6 (8.1 to 8.9, 3 judged) | 0.1158 / 0.3474 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1460 / 0.1377 | 0.1158 / 0.1107 | +0.0301 | +0.0270 |
| num_turns | 7.7 / 8 | 6.3 / 6 | +1.3 | +2 |
| duration_ms | 31390 / 31246 | 40398.7 / 41624 | -9008.7 | -10378 |
| input_tokens | 12.7 / 12 | 12.7 / 12 | 0 | 0 |
| output_tokens | 3080.3 / 3075 | 3536.3 / 3277 | -456 | -202 |
| cache_creation_input_tokens | 22973.7 / 20213 | 14675.7 / 14384 | +8298 | +5829 |
| cache_read_input_tokens | 232281.3 / 223200 | 217221.7 / 203742 | +15059.7 | +19458 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

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
