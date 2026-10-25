# Eval report: workflow-path-audit

- Timestamp: 20261025T204926Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T204757Z-369e42; started 2026-10-25T20:49:26Z, ended 2026-10-25T21:04:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.14, seven_day 0.44 to 0.44, from 10 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.4849 / 1.4546 |
| without_skill | 3 | 0 | 6.3/8 | skipped (objective-decided) | 0.6197 / 1.8591 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4849 / 0.4340 | 0.6197 / 0.5907 | -0.1348 | -0.1567 |
| num_turns | 10.3 / 10 | 11 / 12 | -0.7 | -2 |
| duration_ms | 111531.7 / 96719 | 176503 / 148262 | -64971.3 | -51543 |
| input_tokens | 18.7 / 18 | 22 / 24 | -3.3 | -6 |
| output_tokens | 7229.3 / 6570 | 10387.7 / 9838 | -3158.3 | -3268 |
| cache_creation_input_tokens | 31728 / 27441 | 28029.7 / 26660 | +3698.3 | +781 |
| cache_read_input_tokens | 398840.3 / 381589 | 455446.3 / 500540 | -56606 | -118951 |
| tool_errors | 0.3 / 0 | 2 / 2 | -1.7 | -2 |

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
