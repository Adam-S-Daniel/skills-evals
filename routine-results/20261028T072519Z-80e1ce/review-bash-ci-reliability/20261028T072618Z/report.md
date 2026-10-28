# Eval report: review-bash-ci-reliability

- Timestamp: 20261028T072618Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T072519Z-80e1ce; started 2026-10-28T07:26:18Z, ended 2026-10-28T07:34:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.07, seven_day 0.26 to 0.26, from 10 snapshots

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/11 | 4.5 (4.2 to 4.7, 3 judged) | 0.3275 / 0.9826 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3275 / 0.3034 |
| num_turns | 9 / 8 |
| duration_ms | 88780.3 / 81374 |
| input_tokens | 15.3 / 14 |
| output_tokens | 6725 / 6287 |
| cache_creation_input_tokens | 16704 / 15668 |
| cache_read_input_tokens | 296096.7 / 265548 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| process-substitution-error-propagates | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 |
| gh-api-failure-not-swallowed | 3/3 |
| git-identity-configured | 3/3 |
| jq-guaranteed-or-replaced | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 |
| commit-signing-safe-for-ci | 0/3 |
| decoy-optional-cleanup-untouched | 0/3 |
| decoy-existing-set-e-untouched | 3/3 |
