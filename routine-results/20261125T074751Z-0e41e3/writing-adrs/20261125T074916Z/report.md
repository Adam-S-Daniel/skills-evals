# Eval report: writing-adrs

- Timestamp: 20261125T074916Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T074751Z-0e41e3; started 2026-11-25T07:49:16Z, ended 2026-11-25T07:50:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.26, judge $0.08, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.1406 / 0.1406 |
| without_skill | 1 | 0 | 7/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.1205 / 0.1205 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1406 / 0.1406 | 0.1205 / 0.1205 | +0.0201 | +0.0201 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 17773 / 17773 | 13477 / 13477 | +4296 | +4296 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1911 / 1911 | 1415 / 1415 | +496 | +496 |
| cache_creation_input_tokens | 27056 / 27056 | 23455 / 23455 | +3601 | +3601 |
| cache_read_input_tokens | 132295 / 132295 | 125237 / 125237 | +7058 | +7058 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
