# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T121721Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T121544Z-bf3052; started 2026-11-07T12:17:21Z, ended 2026-11-07T12:19:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 4 call(s); agent $0.44, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=2)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 11/11 | skipped (objective-decided) | 0.1281 / 0.2563 |
| without_skill | 2 | 0 | 7.5/11 | skipped (objective-decided) | 0.0931 / 0.1863 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1281 / 0.1281 | 0.0931 / 0.0931 | +0.0350 | +0.0350 |
| num_turns | 6 / 6 | 4.5 / 4.5 | +1.5 | +1.5 |
| duration_ms | 27428 / 27428 | 35351.5 / 35351.5 | -7923.5 | -7923.5 |
| input_tokens | 11 / 11 | 9 / 9 | +2 | +2 |
| output_tokens | 2977.5 / 2977.5 | 2648.5 / 2648.5 | +329 | +329 |
| cache_creation_input_tokens | 20859 / 20859 | 12957.5 / 12957.5 | +7901.5 | +7901.5 |
| cache_read_input_tokens | 149058.5 / 149058.5 | 148029.5 / 148029.5 | +1029 | +1029 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 2/2 | 2/2 |
| workflow-file-present | 2/2 | 2/2 |
| process-substitution-error-propagates | 2/2 | 2/2 |
| grep-q-avoids-broken-pipe | 2/2 | 2/2 |
| gh-api-failure-not-swallowed | 2/2 | 2/2 |
| git-identity-configured | 2/2 | 1/2 |
| jq-guaranteed-or-replaced | 2/2 | 0/2 |
| version-read-does-not-depend-on-unguarded-jq | 2/2 | 0/2 |
| commit-signing-safe-for-ci | 2/2 | 0/2 |
| decoy-optional-cleanup-untouched | 2/2 | 2/2 |
| decoy-existing-set-e-untouched | 2/2 | 2/2 |
