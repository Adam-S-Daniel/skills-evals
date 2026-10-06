# Eval report: writing-adrs

- Timestamp: 20261006T222737Z
- Trials per arm: 1

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.292 (Claude Code)`; models used: with_skill=claude-haiku-4-5-20251001, claude-sonnet-5; without_skill=claude-haiku-4-5-20251001, claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | 10.0 (10.0 to 10.0, 1 judged) | 0.2855 / 0.2855 |
| without_skill | 1 | 0 | 2/9 | 0.7 (0.7 to 0.7, 1 judged) | 0.1112 / 0.1112 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2855 / 0.2855 | 0.1112 / 0.1112 | +0.1743 | +0.1743 |
| num_turns | 16 / 16 | 6 / 6 | +10 | +10 |
| duration_ms | 82442 / 82442 | 35076 / 35076 | +47366 | +47366 |
| input_tokens | 30 / 30 | 12 / 12 | +18 | +18 |
| output_tokens | 6083 / 6083 | 2531 / 2531 | +3552 | +3552 |
| cache_creation_input_tokens | 20675 / 20675 | 9111 / 9111 | +11564 | +11564 |
| cache_read_input_tokens | 704904 / 704904 | 242429 / 242429 | +462475 | +462475 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
