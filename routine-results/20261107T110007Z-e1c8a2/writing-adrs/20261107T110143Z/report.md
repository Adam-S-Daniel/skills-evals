# Eval report: writing-adrs

- Timestamp: 20261107T110143Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T110007Z-e1c8a2; started 2026-11-07T11:01:43Z, ended 2026-11-07T11:03:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.58 over 4 call(s); agent $0.58, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: bootstrap (n=2)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 9/9 | skipped (objective-decided) | 0.1554 / 0.3109 |
| without_skill | 2 | 0 | 5/9 | skipped (objective-decided) | 0.1341 / 0.2683 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1554 / 0.1554 | 0.1341 / 0.1341 | +0.0213 | +0.0213 |
| num_turns | 6.5 / 6.5 | 7 / 7 | -0.5 | -0.5 |
| duration_ms | 27623 / 27623 | 21863 / 21863 | +5760 | +5760 |
| input_tokens | 10 / 10 | 11 / 11 | -1 | -1 |
| output_tokens | 2745 / 2745 | 2336 / 2336 | +409 | +409 |
| cache_creation_input_tokens | 28743 / 28743 | 23272 / 23272 | +5471 | +5471 |
| cache_read_input_tokens | 129979 / 129979 | 176749 / 176749 | -46770 | -46770 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 2/2 | 0/2 |
| index-gained-a-row-for-0001 | 2/2 | 0/2 |
| adr-0001-sections-in-order | 2/2 | 0/2 |
| retry-sh-links-the-adr | 2/2 | 2/2 |
| readme-index-links-resolve | 2/2 | 2/2 |
| retry-sh-link-resolves | 2/2 | 2/2 |
| exactly-one-adr-file | 2/2 | 2/2 |
| nothing-else-touched | 2/2 | 2/2 |
| agents-md-gained-the-pointer | 2/2 | 0/2 |
