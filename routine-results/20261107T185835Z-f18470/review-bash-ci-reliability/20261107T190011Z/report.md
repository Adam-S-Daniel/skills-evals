# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T190011Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185835Z-f18470; started 2026-11-07T19:00:11Z, ended 2026-11-07T19:21:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.64, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $5.22 over 6 call(s); agent $5.22, judge $0.00, guard $0.00; last agent call $0.94

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.7/11 | skipped (objective-decided) | 0.7886 / 2.3657 |
| without_skill | 3 | 0 | 5.7/11 | skipped (objective-decided) | 0.9531 / 2.8592 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7886 / 0.7699 | 0.9531 / 0.9424 | -0.1645 | -0.1725 |
| num_turns | 10 / 10 | 12.3 / 10 | -2.3 | 0 |
| duration_ms | 192005 / 189822 | 226180.3 / 221488 | -34175.3 | -31666 |
| input_tokens | 22.7 / 24 | 27.3 / 26 | -4.7 | -2 |
| output_tokens | 12577 / 12889 | 14363 / 11921 | -1786 | +968 |
| cache_creation_input_tokens | 34830.3 / 33680 | 42861 / 42973 | -8030.7 | -9293 |
| cache_read_input_tokens | 361404.3 / 360198 | 574405 / 473665 | -213000.7 | -113467 |
| tool_errors | 1 / 1 | 1 / 0 | 0 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 2/3 | 2/3 |
| grep-q-avoids-broken-pipe | 2/3 | 2/3 |
| gh-api-failure-not-swallowed | 2/3 | 2/3 |
| git-identity-configured | 2/3 | 1/3 |
| jq-guaranteed-or-replaced | 1/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 1/3 | 0/3 |
| commit-signing-safe-for-ci | 2/3 | 0/3 |
| decoy-optional-cleanup-untouched | 2/3 | 1/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
