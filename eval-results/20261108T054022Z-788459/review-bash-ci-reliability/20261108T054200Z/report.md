# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T054200Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T054022Z-788459; started 2026-11-08T05:42:00Z, ended 2026-11-08T05:49:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.62 over 2 call(s); agent $1.62, judge $0.00, guard $0.00; last agent call $0.84

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/11 | skipped (objective-decided) | 0.7784 / 0.7784 |
| without_skill | 1 | 0 | 4/11 | skipped (objective-decided) | 0.8400 / 0.8400 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7784 / 0.7784 | 0.8400 / 0.8400 | -0.0616 | -0.0616 |
| num_turns | 9 / 9 | 11 / 11 | -2 | -2 |
| duration_ms | 190656 / 190656 | 239863 / 239863 | -49207 | -49207 |
| input_tokens | 18 / 18 | 26 / 26 | -8 | -8 |
| output_tokens | 9959 / 9959 | 11295 / 11295 | -1336 | -1336 |
| cache_creation_input_tokens | 42049 / 42049 | 30550 / 30550 | +11499 | +11499 |
| cache_read_input_tokens | 256201 / 256201 | 453271 / 453271 | -197070 | -197070 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 1/1 | 0/1 |
| grep-q-avoids-broken-pipe | 1/1 | 0/1 |
| gh-api-failure-not-swallowed | 0/1 | 0/1 |
| git-identity-configured | 1/1 | 0/1 |
| jq-guaranteed-or-replaced | 1/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 1/1 | 0/1 |
| commit-signing-safe-for-ci | 1/1 | 0/1 |
| decoy-optional-cleanup-untouched | 0/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
