# Eval report: fan-out-triage

- Timestamp: 20261109T182534Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T182410Z-c5e86d; started 2026-11-09T18:25:34Z, ended 2026-11-09T18:27:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.97 over 6 call(s); agent $0.63, judge $0.34, guard $0.00; last agent call $0.17

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/7 | 7.7 (6.0 to 9.4, 3 judged) | 0.2109 / 0.6327 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2109 / 0.1739 |
| num_turns | 4.7 / 4 |
| duration_ms | 31972 / 33677 |
| input_tokens | 9.3 / 8 |
| output_tokens | 3365 / 3379 |
| cache_creation_input_tokens | 22345 / 12701 |
| cache_read_input_tokens | 159211 / 142496 |
| tool_errors | 0.7 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inventory-cites-real-lines | 0/3 |
| one-chunk-file-per-source | 0/3 |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| affected-items-found-and-decoys-not-strong | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
