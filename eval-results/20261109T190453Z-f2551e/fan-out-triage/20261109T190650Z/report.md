# Eval report: fan-out-triage

- Timestamp: 20261109T190650Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T190453Z-f2551e; started 2026-11-09T19:06:50Z, ended 2026-11-09T19:09:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.21 over 6 call(s); agent $0.73, judge $0.47, guard $0.00; last agent call $0.22

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/12 | 8.3 (7.8 to 8.8, 2 judged); 1 judge error(s) | 0.2446 / 0.7338 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2446 / 0.2395 |
| num_turns | 6.3 / 6 |
| duration_ms | 46513.3 / 44727 |
| input_tokens | 11.3 / 12 |
| output_tokens | 4596.7 / 4417 |
| cache_creation_input_tokens | 21375.3 / 20546 |
| cache_read_input_tokens | 228779 / 241939 |
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
