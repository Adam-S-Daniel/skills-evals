# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T051858Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T051726Z-79ebb7; started 2026-11-03T05:18:58Z, ended 2026-11-03T05:20:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 11/11 | skipped (objective-decided) | 0.1519 / 0.1519 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.1436 / 0.1436 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1519 / 0.1519 | 0.1436 / 0.1436 | +0.0083 | +0.0083 |
| num_turns | 6 / 6 | 8 / 8 | -2 | -2 |
| duration_ms | 26119 / 26119 | 48702 / 48702 | -22583 | -22583 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 3040 / 3040 | 5273 / 5273 | -2233 | -2233 |
| cache_creation_input_tokens | 26309 / 26309 | 16453 / 16453 | +9856 | +9856 |
| cache_read_input_tokens | 162402 / 162402 | 250160 / 250160 | -87758 | -87758 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 1/1 | 1/1 |
| git-identity-configured | 1/1 | 1/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 1/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
