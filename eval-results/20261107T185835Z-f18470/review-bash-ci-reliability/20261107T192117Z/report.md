# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T192117Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185835Z-f18470; started 2026-11-07T19:21:17Z, ended 2026-11-07T19:24:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.65 over 6 call(s); agent $0.65, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: release-pipeline (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10.7/11 | skipped (objective-decided) | 0.1182 / 0.3545 |
| without_skill | 3 | 0 | 7.7/11 | skipped (objective-decided) | 0.0979 / 0.2936 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1182 / 0.1061 | 0.0979 / 0.0962 | +0.0203 | +0.0099 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 25209.7 / 24767 | 27054 / 26547 | -1844.3 | -1780 |
| input_tokens | 10.7 / 10 | 8 / 8 | +2.7 | +2 |
| output_tokens | 2770.3 / 2719 | 2940.7 / 2753 | -170.3 | -34 |
| cache_creation_input_tokens | 18998.7 / 15485 | 13849.7 / 13900 | +5149 | +1585 |
| cache_read_input_tokens | 144335.7 / 135244 | 130367.3 / 130495 | +13968.3 | +4749 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| process-substitution-error-propagates | 3/3 | 3/3 |
| grep-q-avoids-broken-pipe | 3/3 | 3/3 |
| gh-api-failure-not-swallowed | 3/3 | 3/3 |
| git-identity-configured | 3/3 | 2/3 |
| jq-guaranteed-or-replaced | 3/3 | 0/3 |
| version-read-does-not-depend-on-unguarded-jq | 3/3 | 0/3 |
| commit-signing-safe-for-ci | 3/3 | 0/3 |
| decoy-optional-cleanup-untouched | 2/3 | 3/3 |
| decoy-existing-set-e-untouched | 3/3 | 3/3 |
