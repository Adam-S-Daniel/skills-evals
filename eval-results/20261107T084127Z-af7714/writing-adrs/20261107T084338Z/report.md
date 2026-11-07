# Eval report: writing-adrs

- Timestamp: 20261107T084338Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T084127Z-af7714; started 2026-11-07T08:43:38Z, ended 2026-11-07T08:44:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1741 / 0.1741 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1174 / 0.1174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1741 / 0.1741 | 0.1174 / 0.1174 | +0.0567 | +0.0567 |
| num_turns | 12 / 12 | 4 / 4 | +8 | +8 |
| duration_ms | 28866 / 28866 | 17687 / 17687 | +11179 | +11179 |
| input_tokens | 16 / 16 | 8 / 8 | +8 | +8 |
| output_tokens | 3294 / 3294 | 1391 / 1391 | +1903 | +1903 |
| cache_creation_input_tokens | 28865 / 28865 | 22841 / 22841 | +6024 | +6024 |
| cache_read_input_tokens | 256868 / 256868 | 121587 / 121587 | +135281 | +135281 |
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
