# Eval report: writing-adrs

- Timestamp: 20261107T123154Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T123013Z-b87b2c; started 2026-11-07T12:31:54Z, ended 2026-11-07T12:33:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 4 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=2)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1571 / 0.3141 |
| without_skill | 2 | 0 | 6.5/7 | skipped (objective-decided) | 0.1186 / 0.2373 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1571 / 0.1571 | 0.1186 / 0.1186 | +0.0384 | +0.0384 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 29925.5 / 29925.5 | 14785.5 / 14785.5 | +15140 | +15140 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 2484 / 2484 | 1397 / 1397 | +1087 | +1087 |
| cache_creation_input_tokens | 27730 / 27730 | 23118 / 23118 | +4612 | +4612 |
| cache_read_input_tokens | 212698.5 / 212698.5 | 121694.5 / 121694.5 | +91004 | +91004 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 2/2 | 2/2 |
| index-gained-a-row-for-0004 | 2/2 | 2/2 |
| retry-sh-links-the-adr | 2/2 | 1/2 |
| readme-index-links-resolve | 2/2 | 2/2 |
| retry-sh-link-resolves | 2/2 | 2/2 |
| exactly-one-new-adr-file | 2/2 | 2/2 |
| nothing-else-touched | 2/2 | 2/2 |
