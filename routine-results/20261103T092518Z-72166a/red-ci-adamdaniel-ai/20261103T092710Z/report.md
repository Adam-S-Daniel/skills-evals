# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T092710Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T092518Z-72166a; started 2026-11-03T09:27:10Z, ended 2026-11-03T09:30:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.13 over 4 call(s); agent $0.68, judge $0.45, guard $0.00; last agent call $0.31

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 2.5 (2.5 to 2.5, 1 judged) | 0.3705 / 0.3705 |
| without_skill | 1 | 0 | 2/3 | 4.5 (4.5 to 4.5, 1 judged) | 0.3102 / 0.3102 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3705 / 0.3705 | 0.3102 / 0.3102 | +0.0602 | +0.0602 |
| num_turns | 6 / 6 | 8 / 8 | -2 | -2 |
| duration_ms | 94311 / 94311 | 77140 / 77140 | +17171 | +17171 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3843 / 3843 | 4125 / 4125 | -282 | -282 |
| cache_creation_input_tokens | 30278 / 30278 | 19848 / 19848 | +10430 | +10430 |
| cache_read_input_tokens | 214338 / 214338 | 309264 / 309264 | -94926 | -94926 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
