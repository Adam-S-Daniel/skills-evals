# Eval report: writing-adrs

- Timestamp: 20261006T192519Z
- Trials per arm: 1

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.292 (Claude Code)`; models used: with_skill=claude-haiku-4-5-20251001, claude-sonnet-5; without_skill=claude-haiku-4-5-20251001, claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | 9.8 (9.8 to 9.8, 1 judged) | 0.3829 / 0.3829 |
| without_skill | 1 | 0 | 2/9 | 1.2 (1.2 to 1.2, 1 judged) | 0.1000 / 0.1000 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3829 / 0.3829 | 0.1000 / 0.1000 | +0.2830 | +0.2830 |
| num_turns | 13 / 13 | 5 / 5 | +8 | +8 |
| duration_ms | 91678 / 91678 | 35115 / 35115 | +56563 | +56563 |
| input_tokens | 24 / 24 | 10 / 10 | +14 | +14 |
| output_tokens | 6731 / 6731 | 2370 / 2370 | +4361 | +4361 |
| cache_creation_input_tokens | 52799 / 52799 | 8812 / 8812 | +43987 | +43987 |
| cache_read_input_tokens | 516978 / 516978 | 200113 / 200113 | +316865 | +316865 |
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
