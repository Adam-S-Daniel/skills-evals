# Eval report: writing-adrs

- Timestamp: 20261107T165154Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T164430Z-7a81dd; started 2026-11-07T16:51:54Z, ended 2026-11-07T16:53:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 6 call(s); agent $0.78, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1420 / 0.4260 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1175 / 0.3524 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1420 / 0.1395 | 0.1175 / 0.1180 | +0.0245 | +0.0215 |
| num_turns | 7 / 6 | 4 / 4 | +3 | +2 |
| duration_ms | 18688.3 / 17816 | 17406.7 / 16184 | +1281.7 | +1632 |
| input_tokens | 10.7 / 10 | 8 / 8 | +2.7 | +2 |
| output_tokens | 1871 / 1748 | 1326 / 1373 | +545 | +375 |
| cache_creation_input_tokens | 27237 / 27254 | 22999.3 / 22992 | +4237.7 | +4262 |
| cache_read_input_tokens | 143315.7 / 129583 | 121947.3 / 121951 | +21368.3 | +7632 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
