# Eval report: writing-adrs

- Timestamp: 20261125T072305Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T072139Z-2d22ee; started 2026-11-25T07:23:05Z, ended 2026-11-25T07:23:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.1419 / 0.1419 |
| without_skill | 1 | 0 | 6/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.1199 / 0.1199 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1419 / 0.1419 | 0.1199 / 0.1199 | +0.0220 | +0.0220 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 17126 / 17126 | 14168 / 14168 | +2958 | +2958 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1972 / 1972 | 1428 / 1428 | +544 | +544 |
| cache_creation_input_tokens | 27234 / 27234 | 23287 / 23287 | +3947 | +3947 |
| cache_read_input_tokens | 132363 / 132363 | 125014 / 125014 | +7349 | +7349 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
