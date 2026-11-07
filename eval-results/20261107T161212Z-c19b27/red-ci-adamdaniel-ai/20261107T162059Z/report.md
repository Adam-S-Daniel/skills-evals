# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T162059Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161212Z-c19b27; started 2026-11-07T16:20:59Z, ended 2026-11-07T16:23:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.53, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 12 call(s); agent $0.55, judge $0.17, guard $0.00; last agent call $0.08

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1.7/3 | 3.3 (3.0 to 4.0, 3 judged) | 0.0993 / 0.2978 |
| without_skill | 3 | 0 | 1.7/3 | 3.7 (3.0 to 4.5, 3 judged) | 0.0851 / 0.2553 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0993 / 0.0866 | 0.0851 / 0.0864 | +0.0142 | +0.0002 |
| num_turns | 5.3 / 5 | 5.3 / 5 | 0 | 0 |
| duration_ms | 20185.7 / 18544 | 18601.7 / 17976 | +1584 | +568 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1152.3 / 1235 | 1183 / 1284 | -30.7 | -49 |
| cache_creation_input_tokens | 17582.7 / 14113 | 13897.3 / 13880 | +3685.3 | +233 |
| cache_read_input_tokens | 173977 / 177491 | 176553.7 / 176588 | -2576.7 | +903 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/3 | 0/3 |
| timeout-kept-on-a-work-job | 3/3 | 3/3 |
| readme-untouched | 2/3 | 2/3 |
