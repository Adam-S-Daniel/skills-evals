# Eval report: writing-adrs

- Timestamp: 20261006T194334Z
- Trials per arm: 1

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.292 (Claude Code)`; models used: with_skill=claude-haiku-4-5-20251001, claude-sonnet-5; without_skill=claude-haiku-4-5-20251001, claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | 9.1 (9.1 to 9.1, 1 judged) | 0.2499 / 0.2499 |
| without_skill | 1 | 0 | 2/9 | 1.0 (1.0 to 1.0, 1 judged) | 0.1241 / 0.1241 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2499 / 0.2499 | 0.1241 / 0.1241 | +0.1258 | +0.1258 |
| num_turns | 14 / 14 | 7 / 7 | +7 | +7 |
| duration_ms | 71356 / 71356 | 52757 / 52757 | +18599 | +18599 |
| input_tokens | 26 / 26 | 10 / 10 | +16 | +16 |
| output_tokens | 5542 / 5542 | 4163 / 4163 | +1379 | +1379 |
| cache_creation_input_tokens | 18397 / 18397 | 10524 / 10524 | +7873 | +7873 |
| cache_read_input_tokens | 599250 / 599250 | 196825 / 196825 | +402425 | +402425 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 0/1 |
| nothing-else-touched | 1/1 | 0/1 |
| agents-md-gained-the-pointer | 1/1 | 0/1 |
