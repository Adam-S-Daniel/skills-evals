# Eval report: writing-adrs

- Timestamp: 20261026T033750Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T033632Z-985fb7; started 2026-10-26T03:37:50Z, ended 2026-10-26T03:40:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.02 to 0.02, seven_day 0.54 to 0.54, from 6 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1525 / 0.4576 |
| without_skill | 3 | 0 | 5/9 | skipped (objective-decided) | 0.1224 / 0.3672 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1525 / 0.1509 | 0.1224 / 0.1179 | +0.0302 | +0.0331 |
| num_turns | 6.3 / 6 | 4.7 / 4 | +1.7 | +2 |
| duration_ms | 21951.3 / 21465 | 19375.3 / 18177 | +2576 | +3288 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 2736.3 / 2593 | 1909.3 / 1834 | +827 | +759 |
| cache_creation_input_tokens | 28092 / 28103 | 22513.3 / 22484 | +5578.7 | +5619 |
| cache_read_input_tokens | 128001.3 / 127946 | 132208.3 / 119596 | -4207 | +8350 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
