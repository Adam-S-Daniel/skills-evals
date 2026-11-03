# Eval report: fan-out-triage

- Timestamp: 20261103T220734Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T215829Z-d1f612; started 2026-11-03T22:07:34Z, ended 2026-11-03T22:09:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: three-files (n=1)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1846 / 0.1846 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1087 / 0.1087 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1846 / 0.1846 | 0.1087 / 0.1087 | +0.0759 | +0.0759 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 48504 / 48504 | 30912 / 30912 | +17592 | +17592 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 4728 / 4728 | 3272 / 3272 | +1456 | +1456 |
| cache_creation_input_tokens | 30197 / 30197 | 14735 / 14735 | +15462 | +15462 |
| cache_read_input_tokens | 165285 / 165285 | 170248 / 170248 | -4963 | -4963 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| one-chunk-file-per-source | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-found-and-decoys-not-strong | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
