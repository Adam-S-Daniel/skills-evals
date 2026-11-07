# Eval report: fan-out-triage

- Timestamp: 20261107T183246Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T182254Z-424da2; started 2026-11-07T18:32:46Z, ended 2026-11-07T18:39:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.61, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.31 over 6 call(s); agent $1.31, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/12 | skipped (objective-decided) | 0.2568 / 0.7703 |
| without_skill | 3 | 0 | 1/12 | skipped (objective-decided) | 0.1809 / 0.5426 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2568 / 0.2612 | 0.1809 / 0.1769 | +0.0759 | +0.0843 |
| num_turns | 10 / 10 | 7.7 / 8 | +2.3 | +2 |
| duration_ms | 74839 / 73588 | 47907.3 / 51561 | +26931.7 | +22027 |
| input_tokens | 18 / 18 | 13.3 / 14 | +4.7 | +4 |
| output_tokens | 8403.3 / 8146 | 5058.7 / 5018 | +3344.7 | +3128 |
| cache_creation_input_tokens | 35014 / 33763 | 25867.3 / 24585 | +9146.7 | +9178 |
| cache_read_input_tokens | 326391.3 / 325286 | 267768.7 / 283443 | +58622.7 | +41843 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| inventory-resolves-indirect-uses | 2/3 | 0/3 |
| one-chunk-file-per-source | 0/3 | 0/3 |
| results-follow-the-contract | 1/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| direct-surface-items-strong | 3/3 | 0/3 |
| indirect-surface-items-strong | 3/3 | 0/3 |
| out-of-window-items-not-strong | 3/3 | 0/3 |
| lookalikes-and-filler-not-strong | 3/3 | 0/3 |
| strong-reasons-name-the-file | 3/3 | 0/3 |
| read-count-is-the-item-count | 1/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
