# Eval report: writing-adrs

- Timestamp: 20261107T124834Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T124446Z-06f086; started 2026-11-07T12:48:34Z, ended 2026-11-07T12:49:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 6 call(s); agent $0.21, judge $0.12, guard $0.00; last agent call $0.07

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6/7 | 8.2 (8.2 to 8.2, 3 judged) | 0.0706 / 0.2118 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0706 / 0.0697 |
| num_turns | 4 / 4 |
| duration_ms | 13972.7 / 13815 |
| input_tokens | 8 / 8 |
| output_tokens | 1282 / 1202 |
| cache_creation_input_tokens | 10926.7 / 10914 |
| cache_read_input_tokens | 140444.3 / 140420 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 |
| index-gained-a-row-for-0004 | 3/3 |
| retry-sh-links-the-adr | 0/3 |
| readme-index-links-resolve | 3/3 |
| retry-sh-link-resolves | 3/3 |
| exactly-one-new-adr-file | 3/3 |
| nothing-else-touched | 3/3 |
