# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T163159Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T163016Z-ef96c2; started 2026-11-07T16:31:59Z, ended 2026-11-07T16:49:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.56, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.97 over 6 call(s); agent $3.97, judge $0.00, guard $0.00; last agent call $0.62

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/11 | skipped (objective-decided) | 0.6841 / 2.0524 |
| without_skill | 3 | 0 | 6.7/11 | skipped (objective-decided) | 0.6394 / 1.9181 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6841 / 0.6873 | 0.6394 / 0.6208 | +0.0447 | +0.0665 |
| num_turns | 8 / 8 | 7.3 / 7 | +0.7 | +1 |
| duration_ms | 166296 / 152904 | 178770.7 / 171805 | -12474.7 | -18901 |
| input_tokens | 17.3 / 18 | 17.3 / 16 | 0 | +2 |
| output_tokens | 11039.3 / 10817 | 10468 / 9839 | +571.3 | +978 |
| cache_creation_input_tokens | 31483.7 / 31085 | 27270.7 / 27165 | +4213 | +3920 |
| cache_read_input_tokens | 255018.7 / 275385 | 285549 / 265575 | -30530.3 | +9810 |
| tool_errors | 0.7 / 1 | 1.7 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 3/3 |
| git-identity-configured | 3/3 | 2/3 |
| jq-guaranteed-or-replaced | 3/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 3/3 | 0/3 |
| commit-signing-safe-for-ci | 3/3 | 0/3 |
| decoy-optional-cleanup-untouched | 0/3 | 0/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
