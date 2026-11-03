# Eval report: writing-adrs

- Timestamp: 20261103T234257Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T234047Z-a57a65; started 2026-11-03T23:42:57Z, ended 2026-11-03T23:43:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1574 / 0.1574 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1184 / 0.1184 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1574 / 0.1574 | 0.1184 / 0.1184 | +0.0390 | +0.0390 |
| num_turns | 10 / 10 | 4 / 4 | +6 | +6 |
| duration_ms | 21080 / 21080 | 13655 / 13655 | +7425 | +7425 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 2542 / 2542 | 1430 / 1430 | +1112 | +1112 |
| cache_creation_input_tokens | 27700 / 27700 | 22992 / 22992 | +4708 | +4708 |
| cache_read_input_tokens | 211499 / 211499 | 121410 / 121410 | +90089 | +90089 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
