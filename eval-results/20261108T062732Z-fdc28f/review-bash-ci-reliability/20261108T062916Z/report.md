# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T062916Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T062732Z-fdc28f; started 2026-11-08T06:29:16Z, ended 2026-11-08T06:35:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.96 over 2 call(s); agent $1.96, judge $0.00, guard $0.00; last agent call $1.09

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/11 | skipped (objective-decided) | 0.8700 / 0.8700 |
| without_skill | 1 | 0 | 6/11 | skipped (objective-decided) | 1.0931 / 1.0931 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.8700 / 0.8700 | 1.0931 / 1.0931 | -0.2232 | -0.2232 |
| num_turns | 12 / 12 | 14 / 14 | -2 | -2 |
| duration_ms | 156339 / 156339 | 226119 / 226119 | -69780 | -69780 |
| input_tokens | 24 / 24 | 32 / 32 | -8 | -8 |
| output_tokens | 14644 / 14644 | 15267 / 15267 | -623 | -623 |
| cache_creation_input_tokens | 43977 / 43977 | 48442 / 48442 | -4465 | -4465 |
| cache_read_input_tokens | 476161 / 476161 | 672055 / 672055 | -195894 | -195894 |
| tool_errors | 2 / 2 | 2 / 2 | 0 | 0 |

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
| decoy-optional-cleanup-untouched | 0/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
