# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T091104Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T090928Z-5f3511; started 2026-11-03T09:11:04Z, ended 2026-11-03T09:13:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.06 over 4 call(s); agent $0.66, judge $0.40, guard $0.00; last agent call $0.28

## Fixture: concurrency-cancel (n=1)

- Prompt: The `test` check on my PRs keeps ending up cancelled and blocking the merge, with no failing step. Fix the workflow in this repo.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/2 | 8.0 (8.0 to 8.0, 1 judged) | 0.3784 / 0.3784 |
| without_skill | 1 | 0 | 2/2 | 7.5 (7.5 to 7.5, 1 judged) | 0.2793 / 0.2793 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3784 / 0.3784 | 0.2793 / 0.2793 | +0.0991 | +0.0991 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 72889 / 72889 | 64853 / 64853 | +8036 | +8036 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 4154 / 4154 | 3389 / 3389 | +765 | +765 |
| cache_creation_input_tokens | 30489 / 30489 | 18895 / 18895 | +11594 | +11594 |
| cache_read_input_tokens | 214513 / 214513 | 262599 / 262599 | -48086 | -48086 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-concurrency-cancel | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
