# Eval report: writing-adrs

- Timestamp: 20261107T124615Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T124446Z-06f086; started 2026-11-07T12:46:15Z, ended 2026-11-07T12:48:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 6 call(s); agent $0.74, judge $0.44, guard $0.00; last agent call $0.16

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/7 | 8.9 (8.6 to 9.1, 3 judged) | 0.2480 / 0.7439 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2480 / 0.2029 |
| num_turns | 3.7 / 3 |
| duration_ms | 29867.7 / 22863 |
| input_tokens | 7.3 / 6 |
| output_tokens | 2217.7 / 2017 |
| cache_creation_input_tokens | 22436 / 13756 |
| cache_read_input_tokens | 120479.7 / 103534 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 |
| index-gained-a-row-for-0004 | 3/3 |
| retry-sh-links-the-adr | 3/3 |
| readme-index-links-resolve | 3/3 |
| retry-sh-link-resolves | 3/3 |
| exactly-one-new-adr-file | 3/3 |
| nothing-else-touched | 3/3 |
