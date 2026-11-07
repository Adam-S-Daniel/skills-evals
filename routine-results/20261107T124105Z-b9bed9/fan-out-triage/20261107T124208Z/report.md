# Eval report: fan-out-triage

- Timestamp: 20261107T124208Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T124105Z-b9bed9; started 2026-11-07T12:42:08Z, ended 2026-11-07T12:43:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 6 call(s); agent $0.35, judge $0.13, guard $0.00; last agent call $0.07

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/7 | 6.0 (6.0 to 6.0, 3 judged) | 0.1177 / 0.3532 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1177 / 0.0880 |
| num_turns | 4 / 4 |
| duration_ms | 19934 / 21119 |
| input_tokens | 8 / 8 |
| output_tokens | 2133 / 2060 |
| cache_creation_input_tokens | 20816 / 11992 |
| cache_read_input_tokens | 131377.7 / 139909 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inventory-cites-real-lines | 0/3 |
| one-chunk-file-per-source | 0/3 |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| affected-items-found-and-decoys-not-strong | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
