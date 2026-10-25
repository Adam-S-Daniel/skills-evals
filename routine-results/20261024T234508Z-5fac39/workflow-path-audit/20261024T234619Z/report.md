# Eval report: workflow-path-audit

- Timestamp: 20261024T234619Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261024T234508Z-5fac39; started 2026-10-24T23:46:19Z, ended 2026-10-25T00:01:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.01 to 0.03, seven_day 0.36 to 0.36, from 8 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | 8.9 (8.9 to 8.9, 3 judged) | 0.3839 / 1.1518 |
| without_skill | 3 | 0 | 8/8 | 8.2 (7.7 to 8.6, 3 judged) | 0.4718 / 1.4155 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3839 / 0.4020 | 0.4718 / 0.4717 | -0.0879 | -0.0697 |
| num_turns | 18.3 / 18 | 25 / 26 | -6.7 | -8 |
| duration_ms | 113733.7 / 113944 | 163684 / 163270 | -49950.3 | -49326 |
| input_tokens | 26 / 26 | 34 / 34 | -8 | -8 |
| output_tokens | 8979.3 / 8707 | 13342.3 / 13020 | -4363 | -4313 |
| cache_creation_input_tokens | 39802.7 / 40336 | 40086 / 40569 | -283.3 | -233 |
| cache_read_input_tokens | 674452.3 / 674255 | 890006.3 / 895937 | -215554 | -221682 |
| tool_errors | 1 / 1 | 0.7 / 1 | +0.3 | 0 |

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
