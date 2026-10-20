# Eval report: review-bash-ci-reliability

- Timestamp: 20261020T205255Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261020T205139Z-80424c; started 2026-10-20T20:52:55Z, ended 2026-10-20T20:55:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.1, seven_day 0.1 to 0.1, from 8 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.304 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/11 | skipped (objective-decided) | 0.1400 / 0.4199 |
| without_skill | 3 | 0 | 6.7/11 | skipped (objective-decided) | 0.1275 / 0.3826 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1400 / 0.1395 | 0.1275 / 0.1274 | +0.0125 | +0.0121 |
| num_turns | 6.3 / 6 | 4 / 4 | +2.3 | +2 |
| duration_ms | 27088.7 / 26279 | 27138.7 / 27537 | -50 | -1258 |
| input_tokens | 8.7 / 8 | 8 / 8 | +0.7 | 0 |
| output_tokens | 2566 / 2680 | 2449.7 / 2440 | +116.3 | +240 |
| cache_creation_input_tokens | 25368.7 / 25270 | 22967.7 / 23017 | +2401 | +2253 |
| cache_read_input_tokens | 128305.3 / 115897 | 111375.3 / 111387 | +16930 | +4510 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 3/3 |
| git-identity-configured | 3/3 | 1/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 1/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
