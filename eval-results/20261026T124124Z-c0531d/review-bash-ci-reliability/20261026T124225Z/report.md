# Eval report: review-bash-ci-reliability

- Timestamp: 20261026T124225Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T124124Z-c0531d; started 2026-10-26T12:42:25Z, ended 2026-10-26T12:58:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.37 to 0.43, seven_day 0.65 to 0.66, from 11 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/11 | skipped (objective-decided) | 0.6598 / 1.9793 |
| without_skill | 3 | 0 | 4/11 | skipped (objective-decided) | 0.6683 / 2.0048 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6598 / 0.6376 | 0.6683 / 0.6216 | -0.0085 | +0.0160 |
| num_turns | 9.7 / 10 | 8.7 / 9 | +1 | +1 |
| duration_ms | 151986 / 147886 | 169312.3 / 171638 | -17326.3 | -23752 |
| input_tokens | 17.3 / 18 | 17.3 / 18 | 0 | 0 |
| output_tokens | 9602 / 10193 | 9095.7 / 9073 | +506.3 | +1120 |
| cache_creation_input_tokens | 30870.7 / 27602 | 29512 / 25828 | +1358.7 | +1774 |
| cache_read_input_tokens | 337770 / 360153 | 338973.7 / 341572 | -1203.7 | +18581 |
| tool_errors | 1.7 / 0 | 3.3 / 1 | -1.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 2/3 | 0/3 |
| grep-q-avoids-broken-pipe | 2/3 | 0/3 |
| gh-api-failure-not-swallowed | 2/3 | 0/3 |
| git-identity-configured | 2/3 | 0/3 |
| jq-guaranteed-or-replaced | 0/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 0/3 | 0/3 |
| commit-signing-safe-for-ci | 0/3 | 0/3 |
| decoy-optional-cleanup-untouched | 3/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
