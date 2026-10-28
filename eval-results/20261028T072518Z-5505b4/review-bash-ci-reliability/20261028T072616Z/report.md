# Eval report: review-bash-ci-reliability

- Timestamp: 20261028T072616Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T072518Z-5505b4; started 2026-10-28T07:26:16Z, ended 2026-10-28T07:28:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.07, seven_day 0.26 to 0.26, from 7 snapshots

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.3/11 | 4.8 (4.5 to 5.3, 3 judged) | 0.0832 / 0.2497 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0832 / 0.0825 |
| num_turns | 4 / 4 |
| duration_ms | 26270.3 / 27340 |
| input_tokens | 8 / 8 |
| output_tokens | 2553 / 2615 |
| cache_creation_input_tokens | 10921.7 / 10813 |
| cache_read_input_tokens | 138899.7 / 138864 |
| tool_errors | 0 / 0 |

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
| decoy-optional-cleanup-untouched | 1/3 |
| decoy-existing-set-e-untouched | 3/3 |
