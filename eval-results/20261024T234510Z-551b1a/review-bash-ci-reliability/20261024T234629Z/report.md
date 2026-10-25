# Eval report: review-bash-ci-reliability

- Timestamp: 20261024T234629Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261024T234510Z-551b1a; started 2026-10-24T23:46:29Z, ended 2026-10-24T23:59:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.02, seven_day 0.36 to 0.36, from 7 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.3/11 | skipped (objective-decided) | 0.3093 / 0.9279 |
| without_skill | 3 | 0 | 5/11 | skipped (objective-decided) | 0.3801 / 1.1404 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3093 / 0.3202 | 0.3801 / 0.4356 | -0.0708 | -0.1154 |
| num_turns | 14.7 / 14 | 14 / 17 | +0.7 | -3 |
| duration_ms | 107570.3 / 105709 | 150061.7 / 172905 | -42491.3 | -67196 |
| input_tokens | 18 / 16 | 22 / 24 | -4 | -8 |
| output_tokens | 9285 / 8846 | 13105 / 15119 | -3820 | -6273 |
| cache_creation_input_tokens | 33409.7 / 34002 | 35324.3 / 36688 | -1914.7 | -2686 |
| cache_read_input_tokens | 413841.3 / 354060 | 538667.7 / 596755 | -124826.3 | -242695 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 1/3 | 1/3 |
| gh-api-failure-not-swallowed | 3/3 | 2/3 |
| git-identity-configured | 3/3 | 0/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 0/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
