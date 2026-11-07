# Eval report: cms-stuck-pr-triage

- Timestamp: 20261107T155226Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155045Z-7deeb2; started 2026-11-07T15:52:26Z, ended 2026-11-07T16:00:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.52, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.67 over 6 call(s); agent $3.67, judge $0.00, guard $0.00; last agent call $0.62

## Fixture: cms-stuck-pr-triage (n=3)

- Prompt: The prod publish loop keeps failing. Why, and what should we do about each open cms PR?
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.5974 / 1.7922 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.6244 / 1.8732 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5974 / 0.5915 | 0.6244 / 0.6224 | -0.0270 | -0.0309 |
| num_turns | 11.7 / 12 | 11.7 / 11 | 0 | +1 |
| duration_ms | 65904.7 / 65946 | 93832.3 / 87481 | -27927.7 | -21535 |
| input_tokens | 21.3 / 22 | 22.7 / 22 | -1.3 | 0 |
| output_tokens | 4976 / 5138 | 6110 / 5826 | -1134 | -688 |
| cache_creation_input_tokens | 49841 / 51209 | 49120.3 / 49181 | +720.7 | +2028 |
| cache_read_input_tokens | 495344 / 500627 | 545781 / 561883 | -50437 | -61256 |
| tool_errors | 0.7 / 0 | 1 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-a-stale-base-named | 3/3 | 2/3 |
| pr-b-missing-required-context-named | 3/3 | 3/3 |
| pr-c-left-alone | 3/3 | 2/3 |
| no-write-attempted | 3/3 | 2/3 |
| loop-log-was-read | 2/3 | 0/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
