# Eval report: writing-adrs

- Timestamp: 20261107T152612Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151829Z-599619; started 2026-11-07T15:26:12Z, ended 2026-11-07T15:29:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.49, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 6 call(s); agent $0.85, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1600 / 0.4799 |
| without_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.1219 / 0.3657 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1600 / 0.1576 | 0.1219 / 0.1228 | +0.0381 | +0.0349 |
| num_turns | 6.7 / 6 | 4.3 / 5 | +2.3 | +1 |
| duration_ms | 34084 / 27230 | 21956.3 / 21832 | +12127.7 | +5398 |
| input_tokens | 10.7 / 10 | 7.3 / 8 | +3.3 | +2 |
| output_tokens | 3008.7 / 3095 | 1869.3 / 1899 | +1139.3 | +1196 |
| cache_creation_input_tokens | 28877.3 / 28429 | 23059 / 22908 | +5818.3 | +5521 |
| cache_read_input_tokens | 143395.3 / 129428 | 109621.7 / 121194 | +33773.7 | +8234 |
| tool_errors | 0.3 / 0 | 0.7 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
