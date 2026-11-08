# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T080430Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T080238Z-55aec9; started 2026-11-08T08:04:30Z, ended 2026-11-08T08:10:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.49 over 2 call(s); agent $1.49, judge $0.00, guard $0.00; last agent call $0.73

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.7660 / 0.7660 |
| without_skill | 1 | 0 | 4/11 | skipped (objective-decided) | 0.7282 / 0.7282 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7660 / 0.7660 | 0.7282 / 0.7282 | +0.0379 | +0.0379 |
| num_turns | 10 / 10 | 9 / 9 | +1 | +1 |
| duration_ms | 157907 / 157907 | 181129 / 181129 | -23222 | -23222 |
| input_tokens | 20 / 20 | 18 / 18 | +2 | +2 |
| output_tokens | 9588 / 9588 | 12757 / 12757 | -3169 | -3169 |
| cache_creation_input_tokens | 39889 / 39889 | 31314 / 31314 | +8575 | +8575 |
| cache_read_input_tokens | 360178 / 360178 | 369030 / 369030 | -8852 | -8852 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 0/1 |
| grep-q-avoids-broken-pipe | 1/1 | 0/1 |
| gh-api-failure-not-swallowed | 1/1 | 0/1 |
| git-identity-configured | 1/1 | 0/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
