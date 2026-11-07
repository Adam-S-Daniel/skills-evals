# Eval report: writing-adrs

- Timestamp: 20261107T042310Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T042033Z-15d392; started 2026-11-07T04:23:10Z, ended 2026-11-07T04:23:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 2 call(s); agent $0.33, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.2112 / 0.2112 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1233 / 0.1233 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2112 / 0.2112 | 0.1233 / 0.1233 | +0.0879 | +0.0879 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 21272 / 21272 | 19038 / 19038 | +2234 | +2234 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2809 / 2809 | 2030 / 2030 | +779 | +779 |
| cache_creation_input_tokens | 42901 / 42901 | 22732 / 22732 | +20169 | +20169 |
| cache_read_input_tokens | 114673 / 114673 | 120598 / 120598 | -5925 | -5925 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
| agents-md-gained-the-pointer | 1/1 | 0/1 |
