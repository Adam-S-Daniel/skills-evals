# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T045116Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T044942Z-967efc; started 2026-11-03T04:51:16Z, ended 2026-11-03T04:52:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.24, judge $0.14, guard $0.00; last agent call $0.08

## Fixture: concurrency-cancel (n=1)

- Prompt: The `test` check on my PRs keeps ending up cancelled and blocking the merge, with no failing step. Fix the workflow in this repo.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/2 | 7.0 (7.0 to 7.0, 1 judged) | 0.1562 / 0.1562 |
| without_skill | 1 | 0 | 2/2 | 7.5 (7.5 to 7.5, 1 judged) | 0.0839 / 0.0839 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1562 / 0.1562 | 0.0839 / 0.0839 | +0.0723 | +0.0723 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 27354 / 27354 | 15213 / 15213 | +12141 | +12141 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 2326 / 2326 | 1103 / 1103 | +1223 | +1223 |
| cache_creation_input_tokens | 26078 / 26078 | 13792 / 13792 | +12286 | +12286 |
| cache_read_input_tokens | 286074 / 286074 | 176435 / 176435 | +109639 | +109639 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-concurrency-cancel | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
