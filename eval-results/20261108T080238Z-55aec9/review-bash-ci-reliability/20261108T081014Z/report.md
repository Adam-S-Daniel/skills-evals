# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T081014Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T080238Z-55aec9; started 2026-11-08T08:10:14Z, ended 2026-11-08T08:11:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.1448 / 0.1448 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.0872 / 0.0872 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1448 / 0.1448 | 0.0872 / 0.0872 | +0.0576 | +0.0576 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 23535 / 23535 | 22759 / 22759 | +776 | +776 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2818 / 2818 | 2420 / 2420 | +398 | +398 |
| cache_creation_input_tokens | 26024 / 26024 | 12485 / 12485 | +13539 | +13539 |
| cache_read_input_tokens | 125152 / 125152 | 130100 / 130100 | -4948 | -4948 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 1/1 | 1/1 |
| git-identity-configured | 1/1 | 0/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
