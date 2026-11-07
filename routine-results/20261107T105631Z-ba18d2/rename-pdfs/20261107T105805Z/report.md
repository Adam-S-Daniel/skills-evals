# Eval report: rename-pdfs

- Timestamp: 20261107T105805Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T105631Z-ba18d2; started 2026-11-07T10:58:05Z, ended 2026-11-07T11:01:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 8 call(s); agent $0.53, judge $0.00, guard $0.00; last agent call $0.02

## Fixture: rename-pdfs (n=2)

- Prompt: Rename the PDFs in inbox/ per my convention.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 8/8 | skipped (objective-decided) | 0.1640 / 0.3280 |
| without_skill | 2 | 0 | 4/8 | skipped (objective-decided) | 0.1033 / 0.2067 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1640 / 0.1640 | 0.1033 / 0.1033 | +0.0606 | +0.0606 |
| num_turns | 10.5 / 10.5 | 6.5 / 6.5 | +4 | +4 |
| duration_ms | 51721 / 51721 | 33212 / 33212 | +18509 | +18509 |
| input_tokens | 21 / 21 | 13 / 13 | +8 | +8 |
| output_tokens | 3022.5 / 3022.5 | 2414.5 / 2414.5 | +608 | +608 |
| cache_creation_input_tokens | 24414 / 24414 | 14121.5 / 14121.5 | +10292.5 | +10292.5 |
| cache_read_input_tokens | 360636 / 360636 | 226842 / 226842 | +133794 | +133794 |
| tool_errors | 0.5 / 0.5 | 0 / 0 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inbox-renamed-per-convention | 2/2 | 0/2 |
| inbox-content-preserved | 2/2 | 2/2 |
| statement-date-ranged | 2/2 | 0/2 |
| invoice-dated-from-body | 2/2 | 0/2 |
| receipt-left-alone | 2/2 | 2/2 |
| image-only-scan-left-alone | 2/2 | 2/2 |
| duplicate-bills-disambiguated | 2/2 | 0/2 |
| nothing-outside-inbox | 2/2 | 2/2 |
