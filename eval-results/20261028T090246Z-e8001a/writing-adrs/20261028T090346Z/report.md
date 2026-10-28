# Eval report: writing-adrs

- Timestamp: 20261028T090346Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T090246Z-e8001a; started 2026-10-28T09:03:46Z, ended 2026-10-28T09:06:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.27 to 0.27, from 9 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/9 | 5.7 (5.2 to 6.2, 3 judged) | 0.2539 / 0.7618 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2539 / 0.2065 |
| num_turns | 5 / 5 |
| duration_ms | 29614.7 / 28397 |
| input_tokens | 10 / 10 |
| output_tokens | 2486.3 / 2379 |
| cache_creation_input_tokens | 21251.3 / 12832 |
| cache_read_input_tokens | 170222.3 / 178697 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| readme-bootstrapped-in-skill-shape | 0/3 |
| index-gained-a-row-for-0001 | 0/3 |
| adr-0001-sections-in-order | 0/3 |
| retry-sh-links-the-adr | 2/3 |
| readme-index-links-resolve | 3/3 |
| retry-sh-link-resolves | 3/3 |
| exactly-one-adr-file | 2/3 |
| nothing-else-touched | 1/3 |
| agents-md-gained-the-pointer | 0/3 |
