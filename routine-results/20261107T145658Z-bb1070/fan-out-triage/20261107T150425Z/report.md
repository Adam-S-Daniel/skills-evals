# Eval report: fan-out-triage

- Timestamp: 20261107T150425Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T145658Z-bb1070; started 2026-11-07T15:04:25Z, ended 2026-11-07T15:09:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 6 call(s); agent $0.80, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: keyword-lookalikes (n=3)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1501 / 0.4504 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.1166 / 0.3497 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1501 / 0.1413 | 0.1166 / 0.1161 | +0.0336 | +0.0253 |
| num_turns | 8.3 / 8 | 6 / 6 | +2.3 | +2 |
| duration_ms | 53326 / 54210 | 37968 / 36664 | +15358 | +17546 |
| input_tokens | 14.7 / 14 | 12 / 12 | +2.7 | +2 |
| output_tokens | 4303.7 / 4423 | 3758.3 / 3709 | +545.3 | +714 |
| cache_creation_input_tokens | 21178.3 / 18830 | 14600.7 / 14596 | +6577.7 | +4234 |
| cache_read_input_tokens | 223706 / 217345 | 205650.3 / 205549 | +18055.7 | +11796 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| keyword-lookalikes-are-not-strong | 3/3 | 0/3 |
| strong-reasons-name-the-file | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
