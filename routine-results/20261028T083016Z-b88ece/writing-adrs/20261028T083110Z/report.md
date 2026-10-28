# Eval report: writing-adrs

- Timestamp: 20261028T083110Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T083016Z-b88ece; started 2026-10-28T08:31:10Z, ended 2026-10-28T08:32:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.09 to 0.09, seven_day 0.27 to 0.27, from 6 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3/9 | 4.0 (1.4 to 5.6, 3 judged) | 0.0730 / 0.2191 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0730 / 0.0725 |
| num_turns | 4.3 / 4 |
| duration_ms | 18559.7 / 19734 |
| input_tokens | 7.3 / 8 |
| output_tokens | 1538.3 / 1535 |
| cache_creation_input_tokens | 11173.7 / 11233 |
| cache_read_input_tokens | 128122 / 140010 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| readme-bootstrapped-in-skill-shape | 0/3 |
| index-gained-a-row-for-0001 | 0/3 |
| adr-0001-sections-in-order | 0/3 |
| retry-sh-links-the-adr | 0/3 |
| readme-index-links-resolve | 3/3 |
| retry-sh-link-resolves | 3/3 |
| exactly-one-adr-file | 2/3 |
| nothing-else-touched | 1/3 |
| agents-md-gained-the-pointer | 0/3 |
