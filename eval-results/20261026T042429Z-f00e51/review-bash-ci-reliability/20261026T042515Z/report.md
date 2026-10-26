# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T042515Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T042429Z-f00e51; started 2026-10-26T04:25:15Z, ended 2026-10-26T04:28:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.07 to 0.08, seven_day 0.55 to 0.55, from 7 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/11 | skipped (objective-decided) | 0.1136 / 0.3409 |
| without_skill | 3 | 0 | 7/11 | skipped (objective-decided) | 0.0858 / 0.2574 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1136 / 0.1134 | 0.0858 / 0.0863 | +0.0278 | +0.0271 |
| num_turns | 6.3 / 6 | 4 / 4 | +2.3 | +2 |
| duration_ms | 29054 / 26371 | 25672.7 / 26047 | +3381.3 | +324 |
| input_tokens | 8.7 / 8 | 8 / 8 | +0.7 | 0 |
| output_tokens | 2658 / 2405 | 2363.3 / 2380 | +294.7 | +25 |
| cache_creation_input_tokens | 18188.7 / 15448 | 12304.7 / 12388 | +5884 | +3060 |
| cache_read_input_tokens | 142782.7 / 133142 | 129437 / 129406 | +13345.7 | +3736 |
| tool_errors | 0.7 / 0 | 0 / 0 | +0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 3/3 |
| git-identity-configured | 3/3 | 0/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
