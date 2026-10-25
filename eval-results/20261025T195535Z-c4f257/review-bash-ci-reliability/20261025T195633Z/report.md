# Eval report: review-bash-ci-reliability

- Timestamp: 20261025T195633Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T195535Z-c4f257; started 2026-10-25T19:56:33Z, ended 2026-10-25T20:19:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.06 to 0.08, seven_day 0.43 to 0.43, from 8 snapshots

## Fixture: review-bash-ci-reliability (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/11 | 3.8 (3.1 to 4.2, 3 judged) | 0.7975 / 2.3925 |
| without_skill | 3 | 0 | 6/11 | 3.9 (3.7 to 4.2, 3 judged) | 0.5738 / 1.7215 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.7975 / 0.8589 | 0.5738 / 0.5719 | +0.2237 | +0.2870 |
| num_turns | 10 / 9 | 8 / 9 | +2 | 0 |
| duration_ms | 187630.7 / 180657 | 141805.7 / 135669 | +45825 | +44988 |
| input_tokens | 18 / 16 | 15.3 / 16 | +2.7 | 0 |
| output_tokens | 12632.7 / 11904 | 8839.3 / 8753 | +3793.3 | +3151 |
| cache_creation_input_tokens | 38035.7 / 32828 | 24701 / 24750 | +13334.7 | +8078 |
| cache_read_input_tokens | 357309.3 / 288148 | 286041.3 / 302564 | +71268 | -14416 |
| tool_errors | 1 / 0 | 1.7 / 2 | -0.7 | -2 |

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
| decoy-optional-cleanup-untouched | 1/3 | 1/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
