# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T051606Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051432Z-7be1b7; started 2026-11-07T05:16:06Z, ended 2026-11-07T05:17:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 11/11 | skipped (objective-decided) | 0.1475 / 0.1475 |
| without_skill | 1 | 0 | 8/11 | skipped (objective-decided) | 0.1028 / 0.1028 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1475 / 0.1475 | 0.1028 / 0.1028 | +0.0447 | +0.0447 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 23835 / 23835 | 30371 / 30371 | -6536 | -6536 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3029 / 3029 | 3446 / 3446 | -417 | -417 |
| cache_creation_input_tokens | 26171 / 26171 | 13815 / 13815 | +12356 | +12356 |
| cache_read_input_tokens | 125398 / 125398 | 130630 / 130630 | -5232 | -5232 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
| decoy-optional-cleanup-untouched | 1/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
