# Eval report: fan-out-triage

- Timestamp: 20261107T144701Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143534Z-1db8f2; started 2026-11-07T14:47:01Z, ended 2026-11-07T14:53:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.47, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.26 over 6 call(s); agent $1.26, judge $0.00, guard $0.00; last agent call $0.19

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.3/12 | skipped (objective-decided) | 0.2306 / 0.6919 |
| without_skill | 3 | 0 | 1/12 | skipped (objective-decided) | 0.1891 / 0.5674 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2306 / 0.2167 | 0.1891 / 0.1892 | +0.0415 | +0.0275 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 65417.3 / 71765 | 54652.7 / 53585 | +10764.7 | +18180 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 7635.3 / 7818 | 6391 / 6399 | +1244.3 | +1419 |
| cache_creation_input_tokens | 31638.7 / 27933 | 25465.7 / 25361 | +6173 | +2572 |
| cache_read_input_tokens | 276919.3 / 274843 | 233300.3 / 235746 | +43619 | +39097 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| inventory-resolves-indirect-uses | 2/3 | 0/3 |
| one-chunk-file-per-source | 0/3 | 0/3 |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| direct-surface-items-strong | 3/3 | 0/3 |
| indirect-surface-items-strong | 3/3 | 0/3 |
| out-of-window-items-not-strong | 3/3 | 0/3 |
| lookalikes-and-filler-not-strong | 2/3 | 0/3 |
| strong-reasons-name-the-file | 3/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
