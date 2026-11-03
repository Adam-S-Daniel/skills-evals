# Eval report: writing-adrs

- Timestamp: 20261103T145133Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T144938Z-766f60; started 2026-11-03T14:51:33Z, ended 2026-11-03T14:53:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 4 call(s); agent $0.67, judge $0.44, guard $0.00; last agent call $0.30

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.1 (9.1 to 9.1, 1 judged) | 0.3722 / 0.3722 |
| without_skill | 1 | 0 | 7/7 | 9.1 (9.1 to 9.1, 1 judged) | 0.2988 / 0.2988 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3722 / 0.3722 | 0.2988 / 0.2988 | +0.0734 | +0.0734 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 56933 / 56933 | 33537 / 33537 | +23396 | +23396 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3967 / 3967 | 3108 / 3108 | +859 | +859 |
| cache_creation_input_tokens | 31113 / 31113 | 25519 / 25519 | +5594 | +5594 |
| cache_read_input_tokens | 219413 / 219413 | 162309 / 162309 | +57104 | +57104 |
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
