# Eval report: writing-adrs

- Timestamp: 20261107T164606Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T164430Z-7a81dd; started 2026-11-07T16:46:06Z, ended 2026-11-07T16:51:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.56, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.64 over 12 call(s); agent $1.87, judge $0.77, guard $0.00; last agent call $0.26

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.2 (9.1 to 9.3, 3 judged) | 0.3391 / 1.0173 |
| without_skill | 3 | 0 | 7/7 | 8.9 (8.6 to 9.1, 3 judged) | 0.2859 / 0.8577 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3391 / 0.3324 | 0.2859 / 0.2934 | +0.0532 | +0.0390 |
| num_turns | 7.7 / 7 | 5.3 / 6 | +2.3 | +1 |
| duration_ms | 51878 / 54362 | 33750.3 / 37567 | +18127.7 | +16795 |
| input_tokens | 12.7 / 12 | 9.3 / 10 | +3.3 | +2 |
| output_tokens | 3273.7 / 3108 | 2665.3 / 2819 | +608.3 | +289 |
| cache_creation_input_tokens | 29515 / 29440 | 25319 / 25549 | +4196 | +3891 |
| cache_read_input_tokens | 187284.7 / 173594 | 149965 / 162947 | +37319.7 | +10647 |
| tool_errors | 1.3 / 1 | 0 / 0 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
