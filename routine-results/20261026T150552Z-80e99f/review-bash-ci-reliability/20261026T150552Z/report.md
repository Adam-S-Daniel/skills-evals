# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T150552Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T150552Z-80e99f; started 2026-10-26T15:05:52Z, ended 2026-10-26T15:23:42Z
- Budget stop: per_run_cap (limit 0.015, weekly meter 0.84, moved 0.02); no trial or judge call started after it
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.75 to 0.84, seven_day 0.82 to 0.84, from 10 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/11 | skipped (objective-decided) | 0.7431 / 2.2293 |
| without_skill | 3 | 1 | 4/11 | skipped (objective-decided) | 0.8286 / 1.6573; 1 unknown |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7431 / 0.7421 | 0.8286 / 0.8286 (2 of 3) | -0.0856 | -0.0865 |
| num_turns | 10.7 / 11 | 10.5 / 10.5 (2 of 3) | +0.2 | +0.5 |
| duration_ms | 189425.3 / 189694 | 243766 / 243766 (2 of 3) | -54340.7 | -54072 |
| input_tokens | 19.3 / 20 | 21 / 21 (2 of 3) | -1.7 | -1 |
| output_tokens | 10694.7 / 10878 | 13887 / 13887 (2 of 3) | -3192.3 | -3009 |
| cache_creation_input_tokens | 33745.3 / 34160 | 37888.5 / 37888.5 (2 of 3) | -4143.2 | -3728.5 |
| cache_read_input_tokens | 389391.7 / 394912 | 426489 / 426489 (2 of 3) | -37097.3 | -31577 |
| tool_errors | 1.7 / 2 | 0.5 / 0.5 (2 of 3) | +1.2 | +1.5 |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- without_skill trial 3: budget_stop: trial not started: the run reached its budget stop (per_run_cap); see usage.budget_stop

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 2/2 |
| workflow-file-present | 3/3 | 2/2 |
| process-substitution-error-propagates | 1/3 | 0/2 |
| grep-q-avoids-broken-pipe | 1/3 | 0/2 |
| gh-api-failure-not-swallowed | 1/3 | 0/2 |
| git-identity-configured | 1/3 | 0/2 |
| jq-guaranteed-or-replaced | 0/3 | 0/2 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/2 |
| commit-signing-safe-for-ci | 0/3 | 0/2 |
| decoy-optional-cleanup-untouched | 3/3 | 2/2 |
| decoy-existing-set-e-untouched | 3/3 | 2/2 |
