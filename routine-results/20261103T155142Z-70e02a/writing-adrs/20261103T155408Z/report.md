# Eval report: writing-adrs

- Timestamp: 20261103T155408Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T155142Z-70e02a; started 2026-11-03T15:54:08Z, ended 2026-11-03T15:54:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.54, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1473 / 0.1473 |
| without_skill | 1 | 0 | 3/9 | skipped (objective-decided) | 0.1191 / 0.1191 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1473 / 0.1473 | 0.1191 / 0.1191 | +0.0282 | +0.0282 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 21545 / 21545 | 20613 / 20613 | +932 | +932 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2386 / 2386 | 1696 / 1696 | +690 | +690 |
| cache_creation_input_tokens | 27643 / 27643 | 22513 / 22513 | +5130 | +5130 |
| cache_read_input_tokens | 128472 / 128472 | 120266 / 120266 | +8206 | +8206 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 0/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 0/1 |
| agents-md-gained-the-pointer | 1/1 | 0/1 |
