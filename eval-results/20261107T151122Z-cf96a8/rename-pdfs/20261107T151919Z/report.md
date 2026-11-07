# Eval report: rename-pdfs

- Timestamp: 20261107T151919Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151122Z-cf96a8; started 2026-11-07T15:19:19Z, ended 2026-11-07T15:24:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.49, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.79 over 12 call(s); agent $0.79, judge $0.00, guard $0.00; last agent call $0.02

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.3/8 | skipped (objective-decided) | 0.1598 / 0.4795 |
| without_skill | 3 | 0 | 4/8 | skipped (objective-decided) | 0.1029 / 0.3086 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1598 / 0.1474 | 0.1029 / 0.0978 | +0.0570 | +0.0496 |
| num_turns | 10.3 / 10 | 7.3 / 6 | +3 | +4 |
| duration_ms | 65978.7 / 61861 | 31310.7 / 31329 | +34668 | +30532 |
| input_tokens | 20.7 / 20 | 14 / 12 | +6.7 | +8 |
| output_tokens | 3054 / 3004 | 2236.7 / 2228 | +817.3 | +776 |
| cache_creation_input_tokens | 23349 / 20165 | 13995.3 / 13724 | +9353.7 | +6441 |
| cache_read_input_tokens | 358531.7 / 348570 | 245028.3 / 206701 | +113503.3 | +141869 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inbox-renamed-per-convention | 1/3 | 0/3 |
| inbox-content-preserved | 3/3 | 3/3 |
| statement-date-ranged | 3/3 | 0/3 |
| invoice-dated-from-body | 3/3 | 0/3 |
| receipt-left-alone | 3/3 | 3/3 |
| image-only-scan-left-alone | 3/3 | 3/3 |
| duplicate-bills-disambiguated | 3/3 | 0/3 |
| nothing-outside-inbox | 3/3 | 3/3 |
