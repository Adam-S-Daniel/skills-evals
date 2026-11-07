# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T145321Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143912Z-1daaa9; started 2026-11-07T14:53:21Z, ended 2026-11-07T14:57:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.47, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.61 over 6 call(s); agent $0.61, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 1 | 7/7 | skipped (objective-decided) | 0.1213 / 0.3639 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.0817 / 0.2451 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1213 / 0.1343 | 0.0817 / 0.0804 | +0.0396 | +0.0539 |
| num_turns | 9.3 / 7 | 4 / 4 | +5.3 | +3 |
| duration_ms | 38871 / 46806 | 37117.7 / 35061 | +1753.3 | +11745 |
| input_tokens | 13.3 / 12 | 8 / 8 | +5.3 | +4 |
| output_tokens | 2255 / 1983 | 1857.7 / 1769 | +397.3 | +214 |
| cache_creation_input_tokens | 19610 / 18127 | 12470.7 / 12366 | +7139.3 | +5761 |
| cache_read_input_tokens | 202951.3 / 166437 | 132091.3 / 132157 | +70860 | +34280 |
| tool_errors | 0.7 / 0 | 0 / 0 | +0.7 | 0 |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- with_skill trial 3: workspace_git_collection_failed: workspace_git_collection_failed: git log exited 128

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 2/2 | 3/3 |
| workflow-file-present | 2/2 | 3/3 |
| fresh-runner | 2/2 | 3/3 |
| signing-on-runner | 2/2 | 0/3 |
| developer-config-untouched | 2/2 | 3/3 |
| build-failure-still-fails | 2/2 | 3/3 |
| docs-untouched | 2/2 | 3/3 |
