# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T085141Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T084959Z-5a437b; started 2026-11-08T08:51:41Z, ended 2026-11-08T08:57:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.47 over 2 call(s); agent $1.47, judge $0.00, guard $0.00; last agent call $0.55

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/11 | skipped (objective-decided) | 0.9179 / 0.9179 |
| without_skill | 1 | 0 | 7/11 | skipped (objective-decided) | 0.5501 / 0.5501 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.9179 / 0.9179 | 0.5501 / 0.5501 | +0.3678 | +0.3678 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 216562 / 216562 | 129134 / 129134 | +87428 | +87428 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 12337 / 12337 | 7937 / 7937 | +4400 | +4400 |
| cache_creation_input_tokens | 43378 / 43378 | 25201 / 25201 | +18177 | +18177 |
| cache_read_input_tokens | 371728 / 371728 | 264000 / 264000 | +107728 | +107728 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

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
| decoy-optional-cleanup-untouched | 0/1 | 0/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
