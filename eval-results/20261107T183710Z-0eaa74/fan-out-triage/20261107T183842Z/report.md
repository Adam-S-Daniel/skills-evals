# Eval report: fan-out-triage

- Timestamp: 20261107T183842Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183710Z-0eaa74; started 2026-11-07T18:38:42Z, ended 2026-11-07T18:44:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.86 over 6 call(s); agent $1.86, judge $0.00, guard $0.00; last agent call $0.25

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3611 / 1.0832 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.2583 / 0.7748 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3611 / 0.3322 | 0.2583 / 0.2578 | +0.1028 | +0.0745 |
| num_turns | 7.7 / 8 | 5.3 / 5 | +2.3 | +3 |
| duration_ms | 66745.7 / 67997 | 47940.3 / 49120 | +18805.3 | +18877 |
| input_tokens | 15.3 / 16 | 10.7 / 10 | +4.7 | +6 |
| output_tokens | 5947.7 / 6250 | 4558.3 / 4554 | +1389.3 | +1696 |
| cache_creation_input_tokens | 24228.3 / 20455 | 16211 / 16204 | +8017.3 | +4251 |
| cache_read_input_tokens | 241043.3 / 248322 | 186876 / 173989 | +54167.3 | +74333 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| one-chunk-file-per-source | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
