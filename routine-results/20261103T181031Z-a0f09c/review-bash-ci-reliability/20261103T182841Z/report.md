# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T182841Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T181031Z-a0f09c; started 2026-11-03T18:28:41Z, ended 2026-11-03T18:34:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.66 over 2 call(s); agent $1.66, judge $0.00, guard $0.00; last agent call $0.79

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.8735 / 0.8735 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.7882 / 0.7882 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.8735 / 0.8735 | 0.7882 / 0.7882 | +0.0852 | +0.0852 |
| num_turns | 9 / 9 | 8 / 8 | +1 | +1 |
| duration_ms | 180865 / 180865 | 178660 / 178660 | +2205 | +2205 |
| input_tokens | 20 / 20 | 18 / 18 | +2 | +2 |
| output_tokens | 13670 / 13670 | 12616 / 12616 | +1054 | +1054 |
| cache_creation_input_tokens | 44702 / 44702 | 40053 / 40053 | +4649 | +4649 |
| cache_read_input_tokens | 313985 / 313985 | 325270 / 325270 | -11285 | -11285 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
| decoy-optional-cleanup-untouched | 0/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
