# Eval report: writing-adrs

- Timestamp: 20261102T232453Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261102T232327Z-cdc21e; started 2026-11-02T23:24:53Z, ended 2026-11-02T23:25:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1571 / 0.1571 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1227 / 0.1227 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1571 / 0.1571 | 0.1227 / 0.1227 | +0.0344 | +0.0344 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 23573 / 23573 | 17584 / 17584 | +5989 | +5989 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2937 / 2937 | 1933 / 1933 | +1004 | +1004 |
| cache_creation_input_tokens | 28685 / 28685 | 22830 / 22830 | +5855 | +5855 |
| cache_read_input_tokens | 129878 / 129878 | 120665 / 120665 | +9213 | +9213 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
| agents-md-gained-the-pointer | 1/1 | 0/1 |
