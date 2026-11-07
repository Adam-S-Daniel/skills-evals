# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T182435Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180840Z-06df9d; started 2026-11-07T18:24:35Z, ended 2026-11-07T18:27:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.62 over 6 call(s); agent $0.62, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1051 / 0.3153 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1006 / 0.3017 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1051 / 0.0899 | 0.1006 / 0.0968 | +0.0045 | -0.0068 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 22519 / 22645 | 28590.3 / 23137 | -6071.3 | -492 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1815.7 / 1771 | 2678.7 / 2361 | -863 | -590 |
| cache_creation_input_tokens | 18389.3 / 14718 | 14175.3 / 14060 | +4214 | +658 |
| cache_read_input_tokens | 133573 / 137029 | 170579 / 168991 | -37006 | -31962 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| fresh-runner | 3/3 | 3/3 |
| signing-on-runner | 3/3 | 0/3 |
| developer-config-untouched | 3/3 | 3/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| docs-untouched | 3/3 | 3/3 |
