# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T092044Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T091927Z-8c9546; started 2026-10-26T09:20:44Z, ended 2026-10-26T09:23:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.03 to 0.04, seven_day 0.57 to 0.58, from 8 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/11 | skipped (objective-decided) | 0.1074 / 0.3221 |
| without_skill | 3 | 0 | 6.7/11 | skipped (objective-decided) | 0.0859 / 0.2576 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1074 / 0.0960 | 0.0859 / 0.0857 | +0.0215 | +0.0104 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 22007.3 / 21355 | 26254.7 / 25201 | -4247.3 | -3846 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 2299.7 / 2256 | 2357.7 / 2336 | -58 | -80 |
| cache_creation_input_tokens | 17843 / 14509 | 12337.7 / 12348 | +5505.3 | +2161 |
| cache_read_input_tokens | 129959.7 / 133267 | 129316 / 129399 | +643.7 | +3868 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
| decoy-optional-cleanup-untouched | 3/3 | 2/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
