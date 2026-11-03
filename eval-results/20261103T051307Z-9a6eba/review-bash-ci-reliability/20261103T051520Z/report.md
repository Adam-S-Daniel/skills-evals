# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T051520Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T051307Z-9a6eba; started 2026-11-03T05:15:20Z, ended 2026-11-03T05:16:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 4 call(s); agent $0.23, judge $0.15, guard $0.00; last agent call $0.10

## Fixture: empty-repo-discovery (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1387 / 0.1387 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.0952 / 0.0952 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1387 / 0.1387 | 0.0952 / 0.0952 | +0.0436 | +0.0436 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 19043 / 19043 | 24388 / 24388 | -5345 | -5345 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1968 / 1968 | 2388 / 2388 | -420 | -420 |
| cache_creation_input_tokens | 25704 / 25704 | 13629 / 13629 | +12075 | +12075 |
| cache_read_input_tokens | 162119 / 162119 | 167397 / 167397 | -5278 | -5278 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| gh-failure-fails-the-job | 1/1 | 1/1 |
| partial-listing-fails-the-job | 1/1 | 1/1 |
| empty-org-still-green | 1/1 | 1/1 |
| listed-repos-still-audited | 1/1 | 1/1 |
| allowlist-untouched | 1/1 | 1/1 |
