# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T185733Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T185539Z-292985; started 2026-11-04T18:57:33Z, ended 2026-11-04T18:58:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 11/11 | skipped (objective-decided) | 0.1450 / 0.1450 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.0898 / 0.0898 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1450 / 0.1450 | 0.0898 / 0.0898 | +0.0552 | +0.0552 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 29436 / 29436 | 26020 / 26020 | +3416 | +3416 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2816 / 2816 | 2292 / 2292 | +524 | +524 |
| cache_creation_input_tokens | 26068 / 26068 | 12566 / 12566 | +13502 | +13502 |
| cache_read_input_tokens | 125346 / 125346 | 165746 / 165746 | -40400 | -40400 |
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
