# Eval report: fan-out-triage

- Timestamp: 20261109T185938Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T185806Z-d79916; started 2026-11-09T18:59:38Z, ended 2026-11-09T19:02:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.05, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 6 call(s); agent $0.70, judge $0.31, guard $0.00; last agent call $0.19

## Fixture: single-file (n=3)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/6 | 9.2 (9.0 to 9.4, 2 judged); 1 judge error(s) | 0.2324 / 0.6972 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2324 / 0.1882 |
| num_turns | 6.3 / 6 |
| duration_ms | 39807 / 39841 |
| input_tokens | 12.7 / 12 |
| output_tokens | 3716.3 / 3632 |
| cache_creation_input_tokens | 22602 / 13464 |
| cache_read_input_tokens | 224994.7 / 221908 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inventory-cites-real-lines | 0/3 |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| affected-items-found-and-decoys-not-strong | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
