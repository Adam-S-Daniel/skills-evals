# Eval report: rename-pdfs

- Timestamp: 20261107T151312Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151122Z-cf96a8; started 2026-11-07T15:13:12Z, ended 2026-11-07T15:19:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.89 over 12 call(s); agent $1.89, judge $0.00, guard $0.00; last agent call $0.04

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.3375 / 1.0125 |
| without_skill | 3 | 0 | 4/8 | skipped (objective-decided) | 0.2927 / 0.8781 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3375 / 0.3334 | 0.2927 / 0.2572 | +0.0448 | +0.0762 |
| num_turns | 9.7 / 9 | 10 / 9 | -0.3 | 0 |
| duration_ms | 66777.7 / 81295 | 49208.3 / 51107 | +17569.3 | +30188 |
| input_tokens | 18.7 / 18 | 17.3 / 18 | +1.3 | 0 |
| output_tokens | 3773 / 3959 | 3298.3 / 3121 | +474.7 | +838 |
| cache_creation_input_tokens | 24747 / 21916 | 19976.7 / 17378 | +4770.3 | +4538 |
| cache_read_input_tokens | 319880.7 / 310219 | 334207.7 / 328081 | -14327 | -17862 |
| tool_errors | 2 / 2 | 0.7 / 1 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inbox-renamed-per-convention | 3/3 | 0/3 |
| inbox-content-preserved | 3/3 | 3/3 |
| statement-date-ranged | 3/3 | 0/3 |
| invoice-dated-from-body | 3/3 | 0/3 |
| receipt-left-alone | 3/3 | 3/3 |
| image-only-scan-left-alone | 3/3 | 3/3 |
| duplicate-bills-disambiguated | 3/3 | 0/3 |
| nothing-outside-inbox | 3/3 | 3/3 |
