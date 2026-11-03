# Eval report: writing-adrs

- Timestamp: 20261103T134743Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T134532Z-0fc186; started 2026-11-03T13:47:43Z, ended 2026-11-03T13:48:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1564 / 0.1564 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1271 / 0.1271 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1564 / 0.1564 | 0.1271 / 0.1271 | +0.0293 | +0.0293 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 26510 / 26510 | 25932 / 25932 | +578 | +578 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2943 / 2943 | 2027 / 2027 | +916 | +916 |
| cache_creation_input_tokens | 28503 / 28503 | 22754 / 22754 | +5749 | +5749 |
| cache_read_input_tokens | 129313 / 129313 | 157581 / 157581 | -28268 | -28268 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
