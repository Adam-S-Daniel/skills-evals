# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T144047Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143912Z-1daaa9; started 2026-11-07T14:40:47Z, ended 2026-11-07T14:53:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.47, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.15 over 6 call(s); agent $3.15, judge $0.00, guard $0.00; last agent call $0.53

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.5423 / 1.6268 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.5086 / 1.5259 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5423 / 0.5352 | 0.5086 / 0.5272 | +0.0336 | +0.0080 |
| num_turns | 10 / 10 | 7.3 / 7 | +2.7 | +3 |
| duration_ms | 117924.7 / 115379 | 127390.3 / 134810 | -9465.7 | -19431 |
| input_tokens | 22 / 22 | 16.7 / 16 | +5.3 | +6 |
| output_tokens | 6898.7 / 7160 | 8006.3 / 8625 | -1107.7 | -1465 |
| cache_creation_input_tokens | 27200.3 / 24939 | 23203 / 23666 | +3997.3 | +1273 |
| cache_read_input_tokens | 349396 / 336788 | 275578.7 / 260799 | +73817.3 | +75989 |
| tool_errors | 0 / 0 | 1.3 / 2 | -1.3 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| fresh-runner | 3/3 | 3/3 |
| signing-on-runner | 3/3 | 0/3 |
| developer-config-untouched | 3/3 | 3/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| docs-untouched | 3/3 | 3/3 |
