# Eval report: writing-adrs

- Timestamp: 20261031T190347Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261031T190211Z-c3e925; started 2026-10-31T19:03:47Z, ended 2026-10-31T19:04:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.72, from 3 snapshots

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1603 / 0.1603 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1242 / 0.1242 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1603 / 0.1603 | 0.1242 / 0.1242 | +0.0362 | +0.0362 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 27018 / 27018 | 17760 / 17760 | +9258 | +9258 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2958 / 2958 | 1935 / 1935 | +1023 | +1023 |
| cache_creation_input_tokens | 28412 / 28412 | 22302 / 22302 | +6110 | +6110 |
| cache_read_input_tokens | 170791 / 170791 | 155885 / 155885 | +14906 | +14906 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
| agents-md-gained-the-pointer | 1/1 | 0/1 |
