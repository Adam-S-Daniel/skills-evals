# Eval report: rename-pdfs

- Timestamp: 20261107T124916Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T124821Z-e4820e; started 2026-11-07T12:49:16Z, ended 2026-11-07T12:51:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 9 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 9 call(s); agent $0.28, judge $0.12, guard $0.00; last agent call $0.01

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/8 | 3.4 (3.2 to 3.7, 3 judged) | 0.0939 / 0.2816 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0939 / 0.0948 |
| num_turns | 6.7 / 7 |
| duration_ms | 28269.3 / 25621 |
| input_tokens | 13.3 / 14 |
| output_tokens | 2263 / 2242 |
| cache_creation_input_tokens | 11712.3 / 11652 |
| cache_read_input_tokens | 243644.3 / 257174 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inbox-renamed-per-convention | 0/3 |
| inbox-content-preserved | 3/3 |
| statement-date-ranged | 0/3 |
| invoice-dated-from-body | 0/3 |
| receipt-left-alone | 3/3 |
| image-only-scan-left-alone | 3/3 |
| duplicate-bills-disambiguated | 0/3 |
| nothing-outside-inbox | 3/3 |
