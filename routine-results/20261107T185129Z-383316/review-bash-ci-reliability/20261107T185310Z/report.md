# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T185310Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185129Z-383316; started 2026-11-07T18:53:10Z, ended 2026-11-07T19:03:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.62, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.73 over 6 call(s); agent $2.73, judge $0.00, guard $0.00; last agent call $0.42

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.4760 / 1.4280 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.4355 / 1.3066 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4760 / 0.4137 | 0.4355 / 0.4248 | +0.0404 | -0.0110 |
| num_turns | 10.7 / 9 | 6.3 / 6 | +4.3 | +3 |
| duration_ms | 99511 / 80772 | 95376 / 94081 | +4135 | -13309 |
| input_tokens | 22.7 / 20 | 14.7 / 14 | +8 | +6 |
| output_tokens | 6089.3 / 5036 | 5624.3 / 5558 | +465 | -522 |
| cache_creation_input_tokens | 26456 / 20986 | 20718 / 20753 | +5738 | +233 |
| cache_read_input_tokens | 361012 / 302180 | 227437.7 / 213022 | +133574.3 | +89158 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| grep-miss-recorded | 3/3 | 3/3 |
| cmp-difference-recorded | 3/3 | 3/3 |
| crash-recorded | 3/3 | 3/3 |
| green-run-and-mismatch-unchanged | 3/3 | 3/3 |
| code-and-fixtures-untouched | 2/3 | 0/3 |
