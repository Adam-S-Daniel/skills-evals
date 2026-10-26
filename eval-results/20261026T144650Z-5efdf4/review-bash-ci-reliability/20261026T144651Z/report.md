# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T144651Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144650Z-5efdf4; started 2026-10-26T14:46:51Z, ended 2026-10-26T14:56:16Z
- Budget stop: per_run_cap (limit 0.015, weekly meter 0.8, moved 0.02); no trial or judge call started after it
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.58 to 0.68, seven_day 0.78 to 0.8, from 6 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=none recorded

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.7/11 | error | 0.7241 / 2.1722 |
| without_skill | 3 | 3 | - | - | -; 3 unknown |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7241 / 0.7093 | - | - | - |
| num_turns | 9.3 / 9 | - | - | - |
| duration_ms | 184138.3 / 167543 | - | - | - |
| input_tokens | 16.7 / 16 | - | - | - |
| output_tokens | 10564.3 / 9244 | - | - | - |
| cache_creation_input_tokens | 32905.3 / 35066 | - | - | - |
| cache_read_input_tokens | 328077.7 / 304827 | - | - | - |
| tool_errors | 1.3 / 1 | - | - | - |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- without_skill trial 1: budget_stop: trial not started: the run reached its budget stop (per_run_cap); see usage.budget_stop
- without_skill trial 2: budget_stop: trial not started: the run reached its budget stop (per_run_cap); see usage.budget_stop
- without_skill trial 3: budget_stop: trial not started: the run reached its budget stop (per_run_cap); see usage.budget_stop

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | - |
| workflow-file-present | 3/3 | - |
| process-substitution-error-propagates | 3/3 | - |
| grep-q-avoids-broken-pipe | 3/3 | - |
| gh-api-failure-not-swallowed | 3/3 | - |
| git-identity-configured | 3/3 | - |
| jq-guaranteed-or-replaced | 0/3 | - |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | - |
| commit-signing-safe-for-ci | 0/3 | - |
| decoy-optional-cleanup-untouched | 2/3 | - |
| decoy-existing-set-e-untouched | 3/3 | - |
