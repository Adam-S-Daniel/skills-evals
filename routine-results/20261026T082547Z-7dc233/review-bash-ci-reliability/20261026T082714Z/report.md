# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T082714Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T082547Z-7dc233; started 2026-10-26T08:27:14Z, ended 2026-10-26T08:47:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0 to 0.03, seven_day 0.57 to 0.57, from 8 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/11 | skipped (objective-decided) | 0.7965 / 2.3896 |
| without_skill | 3 | 0 | 5/11 | skipped (objective-decided) | 0.6952 / 2.0855 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7965 / 0.5638 | 0.6952 / 0.7188 | +0.1014 | -0.1550 |
| num_turns | 12.3 / 12 | 9 / 9 | +3.3 | +3 |
| duration_ms | 218020.3 / 183442 | 183570.3 / 175979 | +34450 | +7463 |
| input_tokens | 22 / 22 | 18 / 18 | +4 | +4 |
| output_tokens | 12391.3 / 12285 | 10761 / 10610 | +1630.3 | +1675 |
| cache_creation_input_tokens | 39632.7 / 27781 | 31071 / 30517 | +8561.7 | -2736 |
| cache_read_input_tokens | 460453.3 / 444965 | 362973.7 / 356823 | +97479.7 | +88142 |
| tool_errors | 4.3 / 2 | 0.3 / 0 | +4 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 2/3 | 1/3 |
| grep-q-avoids-broken-pipe | 2/3 | 1/3 |
| gh-api-failure-not-swallowed | 2/3 | 1/3 |
| git-identity-configured | 2/3 | 1/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 2/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
