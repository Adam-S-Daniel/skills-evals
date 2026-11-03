# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T051133Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T050952Z-fe1e6b; started 2026-11-03T05:11:33Z, ended 2026-11-03T05:12:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.22, judge $0.12, guard $0.00; last agent call $0.09

## Fixture: unpinned-action (n=1)

- Prompt: The `test` job fails at "Set up job" before any of its steps run. Fix it.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/2 | 10.0 (10.0 to 10.0, 1 judged) | 0.1370 / 0.1370 |
| without_skill | 1 | 0 | 2/2 | 9.5 (9.5 to 9.5, 1 judged) | 0.0879 / 0.0879 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1370 / 0.1370 | 0.0879 / 0.0879 | +0.0492 | +0.0492 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 14348 / 14348 | 15133 / 15133 | -785 | -785 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 986 / 986 | 1087 / 1087 | -101 | -101 |
| cache_creation_input_tokens | 25568 / 25568 | 13866 / 13866 | +11702 | +11702 |
| cache_read_input_tokens | 248734 / 248734 | 215153 / 215153 | +33581 | +33581 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| checkout-pinned | 1/1 | 1/1 |
| pins-untouched | 1/1 | 1/1 |
