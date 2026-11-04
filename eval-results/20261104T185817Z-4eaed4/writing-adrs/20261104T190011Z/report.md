# Eval report: writing-adrs

- Timestamp: 20261104T190011Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T185817Z-4eaed4; started 2026-11-04T19:00:11Z, ended 2026-11-04T19:00:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1407 / 0.1407 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1172 / 0.1172 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1407 / 0.1407 | 0.1172 / 0.1172 | +0.0235 | +0.0235 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 14447 / 14447 | 11902 / 11902 | +2545 | +2545 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1884 / 1884 | 1397 / 1397 | +487 | +487 |
| cache_creation_input_tokens | 27237 / 27237 | 22778 / 22778 | +4459 | +4459 |
| cache_read_input_tokens | 128982 / 128982 | 121309 / 121309 | +7673 | +7673 |
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
