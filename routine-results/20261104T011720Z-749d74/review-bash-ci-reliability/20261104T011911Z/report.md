# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T011911Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T011720Z-749d74; started 2026-11-04T01:19:11Z, ended 2026-11-04T01:20:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.25, judge $0.15, guard $0.00; last agent call $0.10

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.1438 / 0.1438 |
| without_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.1029 / 0.1029 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1438 / 0.1438 | 0.1029 / 0.1029 | +0.0409 | +0.0409 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 30726 / 30726 | 32002 / 32002 | -1276 | -1276 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 2068 / 2068 | 2960 / 2960 | -892 | -892 |
| cache_creation_input_tokens | 25697 / 25697 | 13221 / 13221 | +12476 | +12476 |
| cache_read_input_tokens | 203366 / 203366 | 203858 / 203858 | -492 | -492 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
