# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T185644Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185506Z-4b6968; started 2026-11-07T18:56:44Z, ended 2026-11-07T19:07:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.63, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.99 over 6 call(s); agent $2.99, judge $0.00, guard $0.00; last agent call $0.49

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4839 / 1.4517 |
| without_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.5119 / 1.5357 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4839 / 0.5547 | 0.5119 / 0.4996 | -0.0280 | +0.0551 |
| num_turns | 9 / 8 | 9.3 / 9 | -0.3 | -1 |
| duration_ms | 85865.3 / 89114 | 119699 / 119079 | -33833.7 | -29965 |
| input_tokens | 19.3 / 18 | 20.7 / 22 | -1.3 | -4 |
| output_tokens | 5469.3 / 5188 | 7322.3 / 7148 | -1853 | -1960 |
| cache_creation_input_tokens | 28963.3 / 33797 | 22694 / 21902 | +6269.3 | +11895 |
| cache_read_input_tokens | 294982.7 / 257455 | 340620.7 / 353533 | -45638 | -96078 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| every-drifted-file-reported | 3/3 | 1/3 |
| unowned-template-not-fatal | 3/3 | 1/3 |
| clean-tree-still-passes | 3/3 | 3/3 |
| drift-and-missing-still-fail | 3/3 | 3/3 |
| config-data-untouched | 3/3 | 3/3 |
