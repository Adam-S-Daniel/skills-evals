# Eval report: writing-adrs

- Timestamp: 20261031T161929Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261031T161759Z-54d566; started 2026-10-31T16:19:29Z, ended 2026-10-31T16:20:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1575 / 0.1575 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1210 / 0.1210 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1575 / 0.1575 | 0.1210 / 0.1210 | +0.0365 | +0.0365 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 26759 / 26759 | 31689 / 31689 | -4930 | -4930 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2969 / 2969 | 1840 / 1840 | +1129 | +1129 |
| cache_creation_input_tokens | 28720 / 28720 | 22622 / 22622 | +6098 | +6098 |
| cache_read_input_tokens | 128989 / 128989 | 120505 / 120505 | +8484 | +8484 |
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
