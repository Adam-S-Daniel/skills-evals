# Eval report: workflow-path-audit

- Timestamp: 20261026T051401Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T051253Z-df0fb9; started 2026-10-26T05:14:01Z, ended 2026-10-26T05:27:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.11, seven_day 0.55 to 0.56, from 9 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.5982 / 1.7946 |
| without_skill | 3 | 0 | 4.7/8 | skipped (objective-decided) | 0.5870 / 1.7609 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5982 / 0.6086 | 0.5870 / 0.5785 | +0.0112 | +0.0302 |
| num_turns | 10.3 / 11 | 10.3 / 10 | 0 | +1 |
| duration_ms | 118233.3 / 116038 | 152156 / 154547 | -33922.7 | -38509 |
| input_tokens | 18.7 / 20 | 20.7 / 20 | -2 | 0 |
| output_tokens | 7313 / 6826 | 10275.3 / 9887 | -2962.3 | -3061 |
| cache_creation_input_tokens | 36393.7 / 29719 | 26853.7 / 26388 | +9540 | +3331 |
| cache_read_input_tokens | 395028.3 / 411246 | 419211.3 / 401474 | -24183 | +9772 |
| tool_errors | 0.3 / 0 | 2.7 / 2 | -2.3 | -2 |

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
