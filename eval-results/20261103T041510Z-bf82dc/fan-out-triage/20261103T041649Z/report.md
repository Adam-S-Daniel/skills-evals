# Eval report: fan-out-triage

- Timestamp: 20261103T041649Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T041510Z-bf82dc; started 2026-11-03T04:16:49Z, ended 2026-11-03T04:18:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: keyword-lookalikes (n=1)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1707 / 0.1707 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1160 / 0.1160 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1707 / 0.1707 | 0.1160 / 0.1160 | +0.0547 | +0.0547 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 33951 / 33951 | 30591 / 30591 | +3360 | +3360 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3957 / 3957 | 3613 / 3613 | +344 | +344 |
| cache_creation_input_tokens | 27679 / 27679 | 14798 / 14798 | +12881 | +12881 |
| cache_read_input_tokens | 203766 / 203766 | 206246 / 206246 | -2480 | -2480 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| keyword-lookalikes-are-not-strong | 1/1 | 0/1 |
| strong-reasons-name-the-file | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
