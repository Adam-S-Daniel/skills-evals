# Eval report: writing-adrs

- Timestamp: 20261006T195807Z
- Trials per arm: 1

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.292 (Claude Code)`; models used: with_skill=claude-haiku-4-5-20251001, claude-sonnet-5; without_skill=claude-haiku-4-5-20251001, claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | 10.0 (10.0 to 10.0, 1 judged) | 0.2493 / 0.2493 |
| without_skill | 1 | 0 | 2/9 | 0.9 (0.9 to 0.9, 1 judged) | 0.0846 / 0.0846 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2493 / 0.2493 | 0.0846 / 0.0846 | +0.1647 | +0.1647 |
| num_turns | 14 / 14 | 4 / 4 | +10 | +10 |
| duration_ms | 56966 / 56966 | 20803 / 20803 | +36163 | +36163 |
| input_tokens | 26 / 26 | 8 / 8 | +18 | +18 |
| output_tokens | 5666 / 5666 | 1966 / 1966 | +3700 | +3700 |
| cache_creation_input_tokens | 18201 / 18201 | 8136 / 8136 | +10065 | +10065 |
| cache_read_input_tokens | 594321 / 594321 | 157255 / 157255 | +437066 | +437066 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

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
