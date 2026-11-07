# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T161347Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161212Z-c19b27; started 2026-11-07T16:13:47Z, ended 2026-11-07T16:20:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.53, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.02 over 6 call(s); agent $2.02, judge $0.00, guard $0.00; last agent call $0.28

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2.7/3 | skipped (objective-decided) | 0.3900 / 1.1699 |
| without_skill | 3 | 0 | 2/3 | skipped (objective-decided) | 0.2824 / 0.8473 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3900 / 0.3897 | 0.2824 / 0.2823 | +0.1076 | +0.1074 |
| num_turns | 8.3 / 8 | 6.7 / 7 | +1.7 | +1 |
| duration_ms | 67386.7 / 65233 | 73062.3 / 70226 | -5675.7 | -4993 |
| input_tokens | 17.3 / 16 | 14 / 14 | +3.3 | +2 |
| output_tokens | 3939 / 3944 | 3657 / 3572 | +282 | +372 |
| cache_creation_input_tokens | 23668.3 / 20247 | 18862.3 / 18874 | +4806 | +1373 |
| cache_read_input_tokens | 275253.7 / 267149 | 249433.7 / 260933 | +25820 | +6216 |
| tool_errors | 1.3 / 2 | 1.3 / 1 | 0 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 3/3 | 0/3 |
| timeout-kept-on-a-work-job | 3/3 | 3/3 |
| readme-untouched | 2/3 | 3/3 |
