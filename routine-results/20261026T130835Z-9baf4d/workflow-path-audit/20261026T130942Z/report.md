# Eval report: workflow-path-audit

- Timestamp: 20261026T130942Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T130835Z-9baf4d; started 2026-10-26T13:09:42Z, ended 2026-10-26T13:26:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.02 to 0.06, seven_day 0.67 to 0.67, from 9 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.7/8 | 9.1 (8.7 to 9.7, 3 judged) | 0.5244 / 1.5731 |
| without_skill | 3 | 0 | 8/8 | 9.0 (8.7 to 9.6, 3 judged) | 0.5609 / 1.6828 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5244 / 0.5017 | 0.5609 / 0.5477 | -0.0366 | -0.0460 |
| num_turns | 10.7 / 11 | 11 / 11 | -0.3 | 0 |
| duration_ms | 119950 / 120653 | 151621.7 / 142177 | -31671.7 | -21524 |
| input_tokens | 19.3 / 20 | 22 / 22 | -2.7 | -2 |
| output_tokens | 8387.7 / 8388 | 10433.3 / 10448 | -2045.7 | -2060 |
| cache_creation_input_tokens | 33150 / 30198 | 26939 / 26660 | +6211 | +3538 |
| cache_read_input_tokens | 418712.7 / 439565 | 461436.7 / 457297 | -42724 | -17732 |
| tool_errors | 0.7 / 1 | 2 / 2 | -1.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 3/3 |
| lockfile-change-routes-to-installers | 3/3 | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 3/3 |
| required-check-always-fires-and-gates-internally | 2/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
