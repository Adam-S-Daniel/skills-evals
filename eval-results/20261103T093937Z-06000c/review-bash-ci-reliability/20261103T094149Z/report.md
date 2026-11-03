# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T094149Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T093937Z-06000c; started 2026-11-03T09:41:49Z, ended 2026-11-03T09:48:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.43 over 2 call(s); agent $1.43, judge $0.00, guard $0.00; last agent call $0.60

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/11 | skipped (objective-decided) | 0.8338 / 0.8338 |
| without_skill | 1 | 0 | 6/11 | skipped (objective-decided) | 0.5976 / 0.5976 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.8338 / 0.8338 | 0.5976 / 0.5976 | +0.2362 | +0.2362 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 224580 / 224580 | 156437 / 156437 | +68143 | +68143 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 10393 / 10393 | 9131 / 9131 | +1262 | +1262 |
| cache_creation_input_tokens | 40109 / 40109 | 26465 / 26465 | +13644 | +13644 |
| cache_read_input_tokens | 313193 / 313193 | 263940 / 263940 | +49253 | +49253 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 1/1 | 0/1 |
| git-identity-configured | 1/1 | 1/1 |
| jq-guaranteed-or-replaced | 0/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 0/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
