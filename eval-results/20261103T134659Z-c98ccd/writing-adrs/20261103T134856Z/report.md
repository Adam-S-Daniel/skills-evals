# Eval report: writing-adrs

- Timestamp: 20261103T134856Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T134659Z-c98ccd; started 2026-11-03T13:48:56Z, ended 2026-11-03T13:50:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.27, judge $0.16, guard $0.00; last agent call $0.12

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.3 (8.3 to 8.3, 1 judged) | 0.1468 / 0.1468 |
| without_skill | 1 | 0 | 7/7 | 8.5 (8.5 to 8.5, 1 judged) | 0.1217 / 0.1217 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1468 / 0.1468 | 0.1217 / 0.1217 | +0.0250 | +0.0250 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 26795 / 26795 | 18044 / 18044 | +8751 | +8751 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1933 / 1933 | 1649 / 1649 | +284 | +284 |
| cache_creation_input_tokens | 27645 / 27645 | 23261 / 23261 | +4384 | +4384 |
| cache_read_input_tokens | 168162 / 168162 | 121635 / 121635 | +46527 | +46527 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
