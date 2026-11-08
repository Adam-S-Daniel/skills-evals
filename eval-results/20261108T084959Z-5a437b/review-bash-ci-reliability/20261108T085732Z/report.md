# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T085732Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T084959Z-5a437b; started 2026-11-08T08:57:32Z, ended 2026-11-08T08:58:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.1537 / 0.1537 |
| without_skill | 1 | 0 | 6/11 | skipped (objective-decided) | 0.0911 / 0.0911 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1537 / 0.1537 | 0.0911 / 0.0911 | +0.0626 | +0.0626 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 26599 / 26599 | 23054 / 23054 | +3545 | +3545 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 3081 / 3081 | 2572 / 2572 | +509 | +509 |
| cache_creation_input_tokens | 26559 / 26559 | 13061 / 13061 | +13498 | +13498 |
| cache_read_input_tokens | 166078 / 166078 | 130751 / 130751 | +35327 | +35327 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 0/1 | 1/1 |
| git-identity-configured | 1/1 | 0/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 1/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
