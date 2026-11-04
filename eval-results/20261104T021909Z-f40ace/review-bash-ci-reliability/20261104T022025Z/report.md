# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T022025Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T021909Z-f40ace; started 2026-11-04T02:20:25Z, ended 2026-11-04T02:21:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.86 to 0.86, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.1508 / 0.1508 |
| without_skill | 1 | 0 | 8/11 | skipped (objective-decided) | 0.0958 / 0.0958 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1508 / 0.1508 | 0.0958 / 0.0958 | +0.0550 | +0.0550 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 26188 / 26188 | 26099 / 26099 | +89 | +89 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 3009 / 3009 | 2986 / 2986 | +23 | +23 |
| cache_creation_input_tokens | 26107 / 26107 | 13218 / 13218 | +12889 | +12889 |
| cache_read_input_tokens | 162454 / 162454 | 130669 / 130669 | +31785 | +31785 |
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
| decoy-optional-cleanup-untouched | 0/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
