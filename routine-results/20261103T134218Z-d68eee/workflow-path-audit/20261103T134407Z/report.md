# Eval report: workflow-path-audit

- Timestamp: 20261103T134407Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T134218Z-d68eee; started 2026-11-03T13:44:07Z, ended 2026-11-03T13:46:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 4 call(s); agent $0.32, judge $0.17, guard $0.00; last agent call $0.14

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/8 | 6.4 (6.4 to 6.4, 1 judged) | 0.1844 / 0.1844 |
| without_skill | 1 | 0 | 8/8 | 8.5 (8.5 to 8.5, 1 judged) | 0.1376 / 0.1376 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1844 / 0.1844 | 0.1376 / 0.1376 | +0.0468 | +0.0468 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 42870 / 42870 | 71718 / 71718 | -28848 | -28848 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 3339 / 3339 | 4463 / 4463 | -1124 | -1124 |
| cache_creation_input_tokens | 31253 / 31253 | 16944 / 16944 | +14309 | +14309 |
| cache_read_input_tokens | 259188 / 259188 | 251380 / 251380 | +7808 | +7808 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 1/1 | 1/1 |
| source-change-routes-correctly | 1/1 | 1/1 |
| lockfile-change-routes-to-installers | 1/1 | 1/1 |
| prose-change-runs-nothing-but-the-required-check | 1/1 | 1/1 |
| required-check-always-fires-and-gates-internally | 0/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
