# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T190844Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T184122Z-0e6df0; started 2026-11-03T19:08:44Z, ended 2026-11-03T19:11:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 4 call(s); agent $0.77, judge $0.41, guard $0.00; last agent call $0.42

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 2.5 (2.5 to 2.5, 1 judged) | 0.3496 / 0.3496 |
| without_skill | 1 | 0 | 2/3 | 5.0 (5.0 to 5.0, 1 judged) | 0.4235 / 0.4235 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3496 / 0.3496 | 0.4235 / 0.4235 | -0.0740 | -0.0740 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 58004 / 58004 | 74611 / 74611 | -16607 | -16607 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3268 / 3268 | 4052 / 4052 | -784 | -784 |
| cache_creation_input_tokens | 29188 / 29188 | 20022 / 20022 | +9166 | +9166 |
| cache_read_input_tokens | 211846 / 211846 | 264764 / 264764 | -52918 | -52918 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
