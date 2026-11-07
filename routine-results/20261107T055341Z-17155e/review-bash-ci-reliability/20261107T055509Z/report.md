# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T055509Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055341Z-17155e; started 2026-11-07T05:55:09Z, ended 2026-11-07T05:55:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 11/11 | skipped (objective-decided) | 0.1444 / 0.1444 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.0884 / 0.0884 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1444 / 0.1444 | 0.0884 / 0.0884 | +0.0560 | +0.0560 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 22654 / 22654 | 20232 / 20232 | +2422 | +2422 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2862 / 2862 | 2251 / 2251 | +611 | +611 |
| cache_creation_input_tokens | 25812 / 25812 | 12330 / 12330 | +13482 | +13482 |
| cache_read_input_tokens | 124825 / 124825 | 165237 / 165237 | -40412 | -40412 |
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
| decoy-optional-cleanup-untouched | 1/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
