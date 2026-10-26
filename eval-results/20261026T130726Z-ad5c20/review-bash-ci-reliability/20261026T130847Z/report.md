# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T130847Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T130726Z-ad5c20; started 2026-10-26T13:08:47Z, ended 2026-10-26T13:12:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.02 to 0.03, seven_day 0.66 to 0.67, from 7 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/11 | skipped (objective-decided) | 0.1068 / 0.3203 |
| without_skill | 3 | 0 | 7.3/11 | skipped (objective-decided) | 0.0939 / 0.2817 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1068 / 0.0953 | 0.0939 / 0.0928 | +0.0129 | +0.0025 |
| num_turns | 6 / 6 | 4.3 / 4 | +1.7 | +2 |
| duration_ms | 22960.3 / 22877 | 37402.7 / 39640 | -14442.3 | -16763 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 2329.3 / 2260 | 2762.7 / 2810 | -433.3 | -550 |
| cache_creation_input_tokens | 17627.7 / 14231 | 13039 / 12791 | +4588.7 | +1440 |
| cache_read_input_tokens | 129630.3 / 132892 | 140848.7 / 129202 | -11218.3 | +3690 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

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
| decoy-optional-cleanup-untouched | 3/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
