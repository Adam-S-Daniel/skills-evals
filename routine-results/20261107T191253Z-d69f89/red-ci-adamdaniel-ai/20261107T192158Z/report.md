# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T192158Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T191253Z-d69f89; started 2026-11-07T19:21:58Z, ended 2026-11-07T19:24:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 12 call(s); agent $0.54, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1.3/3 | 3.2 (2.5 to 3.5, 3 judged) | 0.0987 / 0.2960 |
| without_skill | 3 | 0 | 2/3 | 3.5 (3.0 to 4.0, 3 judged) | 0.0818 / 0.2455 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0987 / 0.0876 | 0.0818 / 0.0821 | +0.0168 | +0.0055 |
| num_turns | 5.3 / 5 | 5 / 5 | +0.3 | 0 |
| duration_ms | 13589.3 / 13818 | 17775.7 / 19358 | -4186.3 | -5540 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1099.7 / 1075 | 956 / 968 | +143.7 | +107 |
| cache_creation_input_tokens | 17571.3 / 14221 | 13651.3 / 13676 | +3920 | +545 |
| cache_read_input_tokens | 173735.7 / 177312 | 176440 / 176455 | -2704.3 | +857 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/3 | 0/3 |
| timeout-kept-on-a-work-job | 3/3 | 3/3 |
| readme-untouched | 1/3 | 3/3 |
