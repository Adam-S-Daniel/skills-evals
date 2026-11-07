# Eval report: fan-out-triage

- Timestamp: 20261107T182429Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T182254Z-424da2; started 2026-11-07T18:24:29Z, ended 2026-11-07T18:32:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.66 over 6 call(s); agent $2.66, judge $0.00, guard $0.00; last agent call $0.43

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.3/12 | skipped (objective-decided) | 0.4780 / 1.4341 |
| without_skill | 3 | 0 | 1/12 | skipped (objective-decided) | 0.4094 / 1.2281 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4780 / 0.4684 | 0.4094 / 0.4311 | +0.0687 | +0.0373 |
| num_turns | 8 / 7 | 6.3 / 7 | +1.7 | 0 |
| duration_ms | 86932.3 / 85831 | 73893 / 71917 | +13039.3 | +13914 |
| input_tokens | 14.7 / 14 | 12 / 12 | +2.7 | +2 |
| output_tokens | 7830.3 / 7819 | 6981.7 / 7277 | +848.7 | +542 |
| cache_creation_input_tokens | 33064.3 / 30737 | 27598.7 / 28354 | +5465.7 | +2383 |
| cache_read_input_tokens | 284236.3 / 289982 | 244454 / 246492 | +39782.3 | +43490 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/3 | 0/3 |
| inventory-resolves-indirect-uses | 0/3 | 0/3 |
| one-chunk-file-per-source | 0/3 | 0/3 |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 1/3 | 0/3 |
| direct-surface-items-strong | 1/3 | 0/3 |
| indirect-surface-items-strong | 1/3 | 0/3 |
| out-of-window-items-not-strong | 1/3 | 0/3 |
| lookalikes-and-filler-not-strong | 1/3 | 0/3 |
| strong-reasons-name-the-file | 1/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
