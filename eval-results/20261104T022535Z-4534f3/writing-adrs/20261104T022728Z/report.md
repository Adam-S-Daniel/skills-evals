# Eval report: writing-adrs

- Timestamp: 20261104T022728Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T022535Z-4534f3; started 2026-11-04T02:27:28Z, ended 2026-11-04T02:28:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.86 to 0.86, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1384 / 0.1384 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1174 / 0.1174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1384 / 0.1384 | 0.1174 / 0.1174 | +0.0211 | +0.0211 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 15794 / 15794 | 17218 / 17218 | -1424 | -1424 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1864 / 1864 | 1419 / 1419 | +445 | +445 |
| cache_creation_input_tokens | 26724 / 26724 | 22761 / 22761 | +3963 | +3963 |
| cache_read_input_tokens | 128771 / 128771 | 121194 / 121194 | +7577 | +7577 |
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
