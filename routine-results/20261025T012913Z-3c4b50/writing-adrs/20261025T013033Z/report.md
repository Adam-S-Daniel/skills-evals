# Eval report: writing-adrs

- Timestamp: 20261025T013033Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T012913Z-3c4b50; started 2026-10-25T01:30:33Z, ended 2026-10-25T01:40:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.09, seven_day 0.37 to 0.37, from 7 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.3/9 | skipped (objective-decided) | 0.3679 / 1.1037 |
| without_skill | 3 | 0 | 2.7/9 | skipped (objective-decided) | 0.2313 / 0.6939 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3679 / 0.3327 | 0.2313 / 0.2283 | +0.1366 | +0.1044 |
| num_turns | 17.7 / 16 | 6.7 / 6 | +11 | +10 |
| duration_ms | 99250.3 / 86491 | 93594.7 / 95759 | +5655.7 | -9268 |
| input_tokens | 28.7 / 26 | 12 / 12 | +16.7 | +14 |
| output_tokens | 7835.3 / 7040 | 7320 / 7118 | +515.3 | -78 |
| cache_creation_input_tokens | 36232 / 35560 | 26882 / 26560 | +9350 | +9000 |
| cache_read_input_tokens | 722826 / 633148 | 252670.7 / 254103 | +470155.3 | +379045 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 0/3 |
| nothing-else-touched | 3/3 | 2/3 |
| agents-md-gained-the-pointer | 1/3 | 0/3 |
