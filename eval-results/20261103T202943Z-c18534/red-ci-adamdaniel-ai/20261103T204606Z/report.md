# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T204606Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T202943Z-c18534; started 2026-11-03T20:46:06Z, ended 2026-11-03T20:49:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.08 over 4 call(s); agent $0.67, judge $0.41, guard $0.00; last agent call $0.33

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 2.5 (2.5 to 2.5, 1 judged) | 0.3422 / 0.3422 |
| without_skill | 1 | 0 | 2/3 | 3.5 (3.5 to 3.5, 1 judged) | 0.3251 / 0.3251 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3422 / 0.3422 | 0.3251 / 0.3251 | +0.0172 | +0.0172 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 89802 / 89802 | 90445 / 90445 | -643 | -643 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3025 / 3025 | 4785 / 4785 | -1760 | -1760 |
| cache_creation_input_tokens | 28088 / 28088 | 21080 / 21080 | +7008 | +7008 |
| cache_read_input_tokens | 249289 / 249289 | 264998 / 264998 | -15709 | -15709 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
