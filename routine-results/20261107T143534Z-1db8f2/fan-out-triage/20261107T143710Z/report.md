# Eval report: fan-out-triage

- Timestamp: 20261107T143710Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143534Z-1db8f2; started 2026-11-07T14:37:10Z, ended 2026-11-07T14:47:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.46, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $4.69 over 12 call(s); agent $2.69, judge $2.00, guard $0.00; last agent call $0.43

## Fixture: indirect-surfaces (n=3)

- Prompt: We are moving acme from the version pinned in package.json to 3.8.0, the latest stable release. The vendor's whole 3.x changelog is in notes/, one file per minor version. Work out which items change something this repo relies on, and in which file. Keep working files in triage/ and put the final answer in triage/results.tsv. I will paste item text from your file straight into tickets, so every line has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1/12 | 8.4 (8.4 to 8.4, 3 judged) | 0.4704 / 1.4112 |
| without_skill | 3 | 0 | 1/12 | 8.0 (7.2 to 8.4, 3 judged) | 0.4272 / 1.2817 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4704 / 0.5016 | 0.4272 / 0.4309 | +0.0432 | +0.0707 |
| num_turns | 9 / 9 | 7.7 / 7 | +1.3 | +2 |
| duration_ms | 79372.3 / 72676 | 78894 / 73954 | +478.3 | -1278 |
| input_tokens | 14.7 / 14 | 15.3 / 14 | -0.7 | 0 |
| output_tokens | 7521.3 / 7249 | 7003 / 7278 | +518.3 | -29 |
| cache_creation_input_tokens | 32203.3 / 30789 | 27879.7 / 28590 | +4323.7 | +2199 |
| cache_read_input_tokens | 311441 / 287558 | 320433 / 290442 | -8992 | -2884 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 0/3 | 0/3 |
| inventory-resolves-indirect-uses | 0/3 | 0/3 |
| one-chunk-file-per-source | 0/3 | 0/3 |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 0/3 | 0/3 |
| direct-surface-items-strong | 0/3 | 0/3 |
| indirect-surface-items-strong | 0/3 | 0/3 |
| out-of-window-items-not-strong | 0/3 | 0/3 |
| lookalikes-and-filler-not-strong | 0/3 | 0/3 |
| strong-reasons-name-the-file | 0/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
