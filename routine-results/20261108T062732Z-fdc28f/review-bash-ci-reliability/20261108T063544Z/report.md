# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T063544Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T062732Z-fdc28f; started 2026-11-08T06:35:44Z, ended 2026-11-08T06:36:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.1490 / 0.1490 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.1135 / 0.1135 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1490 / 0.1490 | 0.1135 / 0.1135 | +0.0355 | +0.0355 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 23950 / 23950 | 39945 / 39945 | -15995 | -15995 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2903 / 2903 | 3889 / 3889 | -986 | -986 |
| cache_creation_input_tokens | 25945 / 25945 | 14425 / 14425 | +11520 | +11520 |
| cache_read_input_tokens | 162079 / 162079 | 169177 / 169177 | -7098 | -7098 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 1/1 |
| grep-q-avoids-broken-pipe | 1/1 | 1/1 |
| gh-api-failure-not-swallowed | 1/1 | 0/1 |
| git-identity-configured | 1/1 | 1/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
