# Eval report: writing-adrs

- Timestamp: 20261104T022953Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T022815Z-a4fcd5; started 2026-11-04T02:29:53Z, ended 2026-11-04T02:30:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.86 to 0.86, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.1542 / 0.1542 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1173 / 0.1173 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1542 / 0.1542 | 0.1173 / 0.1173 | +0.0369 | +0.0369 |
| num_turns | 6 / 6 | 3 / 3 | +3 | +3 |
| duration_ms | 23134 / 23134 | 17439 / 17439 | +5695 | +5695 |
| input_tokens | 10 / 10 | 6 / 6 | +4 | +4 |
| output_tokens | 2908 / 2908 | 1780 / 1780 | +1128 | +1128 |
| cache_creation_input_tokens | 28060 / 28060 | 22754 / 22754 | +5306 | +5306 |
| cache_read_input_tokens | 129023 / 129023 | 85206 / 85206 | +43817 | +43817 |
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
