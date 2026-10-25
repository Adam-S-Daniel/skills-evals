# Eval report: review-bash-ci-reliability

- Timestamp: 20261025T024449Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T024341Z-f3ddb7; started 2026-10-25T02:44:49Z, ended 2026-10-25T03:06:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.13 to 0.16, seven_day 0.38 to 0.39, from 10 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/11 | skipped (objective-decided) | 0.9273 / 2.7820 |
| without_skill | 3 | 0 | 6/11 | skipped (objective-decided) | 0.8055 / 2.4165 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.9273 / 0.7208 | 0.8055 / 0.6965 | +0.1218 | +0.0243 |
| num_turns | 11.7 / 11 | 9 / 9 | +2.7 | +2 |
| duration_ms | 222587 / 173065 | 206828.3 / 173882 | +15758.7 | -817 |
| input_tokens | 20.7 / 20 | 18 / 18 | +2.7 | +2 |
| output_tokens | 13671.7 / 12686 | 13158.3 / 12432 | +513.3 | +254 |
| cache_creation_input_tokens | 41597 / 34940 | 33135.3 / 30028 | +8461.7 | +4912 |
| cache_read_input_tokens | 452486.7 / 398264 | 375207.3 / 368184 | +77279.3 | +30080 |
| tool_errors | 3.7 / 2 | 2.7 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 2/3 | 2/3 |
| grep-q-avoids-broken-pipe | 2/3 | 2/3 |
| gh-api-failure-not-swallowed | 2/3 | 2/3 |
| git-identity-configured | 2/3 | 2/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 2/3 | 1/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
