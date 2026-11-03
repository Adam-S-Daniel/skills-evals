# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T142911Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T142749Z-e33110; started 2026-11-03T14:29:11Z, ended 2026-11-03T14:30:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.47, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/11 | skipped (objective-decided) | 0.1508 / 0.1508 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.0996 / 0.0996 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1508 / 0.1508 | 0.0996 / 0.0996 | +0.0512 | +0.0512 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 38749 / 38749 | 27774 / 27774 | +10975 | +10975 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3263 / 3263 | 2973 / 2973 | +290 | +290 |
| cache_creation_input_tokens | 26410 / 26410 | 13328 / 13328 | +13082 | +13082 |
| cache_read_input_tokens | 125132 / 125132 | 165681 / 165681 | -40549 | -40549 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 0/1 | 1/1 |
| git-identity-configured | 1/1 | 1/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
