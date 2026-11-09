# Eval report: fan-out-triage

- Timestamp: 20261109T181833Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T181706Z-94af99; started 2026-11-09T18:18:33Z, ended 2026-11-09T18:21:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.58 over 6 call(s); agent $0.46, judge $0.12, guard $0.00; last agent call $0.14

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/12 | 7.5 (6.8 to 7.8, 3 judged) | 0.1539 / 0.4617 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1539 / 0.1416 |
| num_turns | 7.3 / 7 |
| duration_ms | 41563.7 / 43663 |
| input_tokens | 12.7 / 14 |
| output_tokens | 4936 / 5144 |
| cache_creation_input_tokens | 31701 / 22530 |
| cache_read_input_tokens | 252645.7 / 269048 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inventory-cites-real-lines | 0/3 |
| inventory-resolves-indirect-uses | 0/3 |
| one-chunk-file-per-source | 0/3 |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| direct-surface-items-strong | 0/3 |
| indirect-surface-items-strong | 0/3 |
| out-of-window-items-not-strong | 0/3 |
| lookalikes-and-filler-not-strong | 0/3 |
| strong-reasons-name-the-file | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
