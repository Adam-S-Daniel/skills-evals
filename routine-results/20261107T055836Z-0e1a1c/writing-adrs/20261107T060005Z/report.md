# Eval report: writing-adrs

- Timestamp: 20261107T060005Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055836Z-0e1a1c; started 2026-11-07T06:00:05Z, ended 2026-11-07T06:00:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1388 / 0.1388 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1174 / 0.1174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1388 / 0.1388 | 0.1174 / 0.1174 | +0.0214 | +0.0214 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 17281 / 17281 | 14367 / 14367 | +2914 | +2914 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1727 / 1727 | 1396 / 1396 | +331 | +331 |
| cache_creation_input_tokens | 27150 / 27150 | 22809 / 22809 | +4341 | +4341 |
| cache_read_input_tokens | 129105 / 129105 | 121485 / 121485 | +7620 | +7620 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
