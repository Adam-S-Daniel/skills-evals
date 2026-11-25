# Eval report: writing-adrs

- Timestamp: 20261125T114030Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T113859Z-39dc12; started 2026-11-25T11:40:30Z, ended 2026-11-25T11:41:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped: the version with the skill passed more checks (9 of 9 vs 5 of 9) | 0.1704 / 0.1704 |
| without_skill | 1 | 0 | 5/9 | skipped: the version with the skill passed more checks (9 of 9 vs 5 of 9) | 0.1242 / 0.1242 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1704 / 0.1704 | 0.1242 / 0.1242 | +0.0461 | +0.0461 |
| num_turns | 10 / 10 | 4 / 4 | +6 | +6 |
| duration_ms | 25809 / 25809 | 18625 / 18625 | +7184 | +7184 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3791 / 3791 | 2056 / 2056 | +1735 | +1735 |
| cache_creation_input_tokens | 29796 / 29796 | 22817 / 22817 | +6979 | +6979 |
| cache_read_input_tokens | 132378 / 132378 | 123659 / 123659 | +8719 | +8719 |
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
