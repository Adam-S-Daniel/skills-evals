# Eval report: rename-pdfs

- Timestamp: 20261107T193236Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193049Z-7ee4b7; started 2026-11-07T19:32:36Z, ended 2026-11-07T19:37:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.73 over 12 call(s); agent $1.73, judge $0.00, guard $0.00; last agent call $0.04

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/8 | skipped (objective-decided) | 0.3390 / 1.0169 |
| without_skill | 3 | 0 | 4/8 | skipped (objective-decided) | 0.2370 / 0.7110 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3390 / 0.3125 | 0.2370 / 0.2392 | +0.1020 | +0.0733 |
| num_turns | 9.7 / 10 | 6.7 / 7 | +3 | +3 |
| duration_ms | 58941 / 60310 | 38209.7 / 35814 | +20731.3 | +24496 |
| input_tokens | 20.7 / 20 | 13.3 / 14 | +7.3 | +6 |
| output_tokens | 3680.3 / 3465 | 2792 / 2909 | +888.3 | +556 |
| cache_creation_input_tokens | 24811.3 / 22547 | 16598.3 / 16302 | +8213 | +6245 |
| cache_read_input_tokens | 333910.7 / 339778 | 241521 / 252972 | +92389.7 | +86806 |
| tool_errors | 1.7 / 2 | 0.7 / 0 | +1 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inbox-renamed-per-convention | 2/3 | 0/3 |
| inbox-content-preserved | 3/3 | 3/3 |
| statement-date-ranged | 3/3 | 0/3 |
| invoice-dated-from-body | 2/3 | 0/3 |
| receipt-left-alone | 3/3 | 3/3 |
| image-only-scan-left-alone | 3/3 | 3/3 |
| duplicate-bills-disambiguated | 2/3 | 0/3 |
| nothing-outside-inbox | 3/3 | 3/3 |
