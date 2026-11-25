# Eval report: writing-adrs

- Timestamp: 20261125T123516Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T123350Z-43802e; started 2026-11-25T12:35:16Z, ended 2026-11-25T12:36:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.13
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.1503 / 0.1503 |
| without_skill | 1 | 0 | 6/7 | skipped: the version with the skill passed more checks (7 of 7 vs 6 of 7) | 0.1276 / 0.1276 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1503 / 0.1503 | 0.1276 / 0.1276 | +0.0227 | +0.0227 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 18634 / 18634 | 15910 / 15910 | +2724 | +2724 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2218 / 2218 | 1649 / 1649 | +569 | +569 |
| cache_creation_input_tokens | 27670 / 27670 | 23689 / 23689 | +3981 | +3981 |
| cache_read_input_tokens | 174646 / 174646 | 163590 / 163590 | +11056 | +11056 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
