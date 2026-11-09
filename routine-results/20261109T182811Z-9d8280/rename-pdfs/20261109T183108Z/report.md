# Eval report: rename-pdfs

- Timestamp: 20261109T183108Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T182811Z-9d8280; started 2026-11-09T18:31:08Z, ended 2026-11-09T18:33:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 9 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.79 over 9 call(s); agent $0.50, judge $0.29, guard $0.00; last agent call $0.03

## Fixture: rename-pdfs (n=3)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/8 | 4.0 (3.9 to 4.2, 3 judged) | 0.1667 / 0.5001 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1667 / 0.1693 |
| num_turns | 7 / 7 |
| duration_ms | 28393.7 / 28857 |
| input_tokens | 14 / 14 |
| output_tokens | 2387 / 2498 |
| cache_creation_input_tokens | 13250.3 / 13306 |
| cache_read_input_tokens | 263330 / 263439 |
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
