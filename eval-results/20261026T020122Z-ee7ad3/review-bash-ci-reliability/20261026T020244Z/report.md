# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T020244Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T020122Z-ee7ad3; started 2026-10-26T02:02:44Z, ended 2026-10-26T02:05:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.19 to 0.2, seven_day 0.52 to 0.52, from 7 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/11 | skipped (objective-decided) | 0.1243 / 0.3730 |
| without_skill | 3 | 0 | 7/11 | skipped (objective-decided) | 0.0978 / 0.2935 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1243 / 0.0922 | 0.0978 / 0.1008 | +0.0265 | -0.0086 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 22620.3 / 22938 | 29310.7 / 28699 | -6690.3 | -5761 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 2207.3 / 2179 | 2866.7 / 2927 | -659.3 | -748 |
| cache_creation_input_tokens | 22430.3 / 14269 | 13160.3 / 13447 | +9270 | +822 |
| cache_read_input_tokens | 125078.3 / 133205 | 165192 / 164549 | -40113.7 | -31344 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 2/3 |
| git-identity-configured | 3/3 | 1/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
