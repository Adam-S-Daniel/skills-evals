# Eval report: rename-pdfs

- Timestamp: 20261107T193746Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193049Z-7ee4b7; started 2026-11-07T19:37:46Z, ended 2026-11-07T19:42:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 12 call(s); agent $0.78, judge $0.00, guard $0.00; last agent call $0.02

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1582 / 0.4746 |
| without_skill | 3 | 0 | 4/8 | skipped (objective-decided) | 0.1023 / 0.3070 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1582 / 0.1455 | 0.1023 / 0.1076 | +0.0559 | +0.0379 |
| num_turns | 10 / 10 | 7.3 / 8 | +2.7 | +2 |
| duration_ms | 54008 / 54472 | 25705.3 / 25631 | +28302.7 | +28841 |
| input_tokens | 20 / 20 | 14 / 14 | +6 | +6 |
| output_tokens | 3075.3 / 3090 | 2203.3 / 2164 | +872 | +926 |
| cache_creation_input_tokens | 23216 / 19857 | 14226.7 / 14350 | +8989.3 | +5507 |
| cache_read_input_tokens | 345337.7 / 348588 | 233585 / 245788 | +111752.7 | +102800 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inbox-renamed-per-convention | 0/3 | 0/3 |
| inbox-content-preserved | 3/3 | 3/3 |
| statement-date-ranged | 3/3 | 0/3 |
| invoice-dated-from-body | 3/3 | 0/3 |
| receipt-left-alone | 3/3 | 3/3 |
| image-only-scan-left-alone | 3/3 | 3/3 |
| duplicate-bills-disambiguated | 2/3 | 0/3 |
| nothing-outside-inbox | 3/3 | 3/3 |
