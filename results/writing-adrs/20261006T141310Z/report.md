# Eval report: writing-adrs

- Timestamp: 20261006T141310Z
- Trials per arm: 1

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.291 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/9 | 10.0 (10.0 to 10.0, 1 judged) | 0.1538 / 0.1538 |
| without_skill | 1 | 0 | 2/9 | 1.0 (1.0 to 1.0, 1 judged) | 0.0673 / 0.0673 |

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
| agents-md-gained-the-pointer | 0/1 | 0/1 |
