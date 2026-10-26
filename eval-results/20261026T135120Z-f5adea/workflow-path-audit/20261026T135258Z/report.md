# Eval report: workflow-path-audit

- Timestamp: 20261026T135258Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135120Z-f5adea; started 2026-10-26T13:52:58Z, ended 2026-10-26T13:56:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.2, seven_day 0.69 to 0.7, from 11 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1392 / 0.4176 |
| without_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1189 / 0.3566 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1392 / 0.1271 | 0.1189 / 0.1192 | +0.0203 | +0.0079 |
| num_turns | 7 / 7 | 5.7 / 6 | +1.3 | +1 |
| duration_ms | 27741.3 / 26581 | 35940.3 / 36184 | -8199 | -9603 |
| input_tokens | 10.7 / 10 | 11.3 / 12 | -0.7 | -2 |
| output_tokens | 2875.7 / 2779 | 3778.3 / 3639 | -902.7 | -860 |
| cache_creation_input_tokens | 22800 / 19470 | 15439.3 / 15532 | +7360.7 | +3938 |
| cache_read_input_tokens | 192341.7 / 182515 | 193094.7 / 205430 | -753 | -22915 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 2/3 |
| lockfile-change-routes-to-installers | 3/3 | 2/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 2/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 2/3 |
