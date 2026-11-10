# Eval report: review-bash-ci-reliability

- Timestamp: 20261110T072722Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T072533Z-60afff; started 2026-11-10T07:27:22Z, ended 2026-11-10T07:30:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.05 over 6 call(s); agent $0.79, judge $0.26, guard $0.00; last agent call $0.18

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/7 | 8.2 (7.4 to 8.6, 3 judged) | 0.2620 / 0.7860 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2620 / 0.2706 |
| num_turns | 7.7 / 7 |
| duration_ms | 53701 / 47136 |
| input_tokens | 13.3 / 12 |
| output_tokens | 4558.3 / 4311 |
| cache_creation_input_tokens | 24394 / 16355 |
| cache_read_input_tokens | 243994 / 224346 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| fresh-runner | 3/3 |
| signing-on-runner | 3/3 |
| developer-config-untouched | 3/3 |
| build-failure-still-fails | 3/3 |
| docs-untouched | 3/3 |
