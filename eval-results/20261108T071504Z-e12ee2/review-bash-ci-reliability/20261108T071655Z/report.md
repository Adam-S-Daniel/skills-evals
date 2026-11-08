# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T071655Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T071504Z-e12ee2; started 2026-11-08T07:16:55Z, ended 2026-11-08T07:25:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.95 over 3 call(s); agent $1.77, judge $0.18, guard $0.00; last agent call $0.89; 1 call(s) without a dollar figure

## Fixture: release-pipeline (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/11 | error | 0.8790 / 0.8790 |
| without_skill | 1 | 0 | 4/11 | 4.0 (4.0 to 4.0, 1 judged) | 0.8890 / 0.8890 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.8790 / 0.8790 | 0.8890 / 0.8890 | -0.0100 | -0.0100 |
| num_turns | 13 / 13 | 12 / 12 | +1 | +1 |
| duration_ms | 168160 / 168160 | 205496 / 205496 | -37336 | -37336 |
| input_tokens | 28 / 28 | 30 / 30 | -2 | -2 |
| output_tokens | 15701 / 15701 | 12070 / 12070 | +3631 | +3631 |
| cache_creation_input_tokens | 43225 / 43225 | 34472 / 34472 | +8753 | +8753 |
| cache_read_input_tokens | 507111 / 507111 | 521586 / 521586 | -14475 | -14475 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| process-substitution-error-propagates | 0/1 | 0/1 |
| grep-q-avoids-broken-pipe | 0/1 | 0/1 |
| gh-api-failure-not-swallowed | 0/1 | 0/1 |
| git-identity-configured | 0/1 | 0/1 |
| jq-guaranteed-or-replaced | 0/1 | 0/1 |
| version-read-does-not-depend-on-unguarded-jq | 0/1 | 0/1 |
| commit-signing-safe-for-ci | 0/1 | 0/1 |
| decoy-optional-cleanup-untouched | 1/1 | 1/1 |
| decoy-existing-set-e-untouched | 1/1 | 1/1 |
