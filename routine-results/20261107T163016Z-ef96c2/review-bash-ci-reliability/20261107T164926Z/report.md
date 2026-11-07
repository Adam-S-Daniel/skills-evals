# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T164926Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T163016Z-ef96c2; started 2026-11-07T16:49:26Z, ended 2026-11-07T16:52:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 6 call(s); agent $0.64, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | skipped (objective-decided) | 0.1217 / 0.3652 |
| without_skill | 3 | 0 | 7/11 | skipped (objective-decided) | 0.0901 / 0.2702 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1217 / 0.1063 | 0.0901 / 0.0884 | +0.0317 | +0.0180 |
| num_turns | 6.3 / 6 | 4 / 4 | +2.3 | +2 |
| duration_ms | 26758.7 / 26098 | 24723.3 / 25917 | +2035.3 | +181 |
| input_tokens | 11.3 / 10 | 8 / 8 | +3.3 | +2 |
| output_tokens | 2885.3 / 2899 | 2493.3 / 2509 | +392 | +390 |
| cache_creation_input_tokens | 19267 / 15938 | 13025.3 / 12568 | +6241.7 | +3370 |
| cache_read_input_tokens | 157882.3 / 135810 | 130233 / 130365 | +27649.3 | +5445 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 3/3 |
| git-identity-configured | 3/3 | 0/3 |
| jq-guaranteed-or-replaced | 3/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 3/3 | 0/3 |
| commit-signing-safe-for-ci | 3/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
