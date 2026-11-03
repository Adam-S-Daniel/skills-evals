# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T093131Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T092936Z-6a7c5b; started 2026-11-03T09:31:31Z, ended 2026-11-03T09:34:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.88 over 4 call(s); agent $0.52, judge $0.36, guard $0.00; last agent call $0.21

## Fixture: unpinned-action (n=1)

- Prompt: The `test` job fails at "Set up job" before any of its steps run. Fix it.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/2 | 10.0 (10.0 to 10.0, 1 judged) | 0.3113 / 0.3113 |
| without_skill | 1 | 0 | 2/2 | 9.3 (9.3 to 9.3, 1 judged) | 0.2116 / 0.2116 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3113 / 0.3113 | 0.2116 / 0.2116 | +0.0997 | +0.0997 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 74569 / 74569 | 45973 / 45973 | +28596 | +28596 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2432 / 2432 | 1851 / 1851 | +581 | +581 |
| cache_creation_input_tokens | 26974 / 26974 | 15793 / 15793 | +11181 | +11181 |
| cache_read_input_tokens | 208396 / 208396 | 217637 / 217637 | -9241 | -9241 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| checkout-pinned | 1/1 | 1/1 |
| pins-untouched | 1/1 | 1/1 |
