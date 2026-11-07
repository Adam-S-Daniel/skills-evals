# Eval report: fan-out-triage

- Timestamp: 20261107T150932Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150747Z-342890; started 2026-11-07T15:09:32Z, ended 2026-11-07T15:15:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.74 over 6 call(s); agent $1.74, judge $0.00, guard $0.00; last agent call $0.24

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.3334 / 1.0003 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.2480 / 0.7441 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3334 / 0.3014 | 0.2480 / 0.2468 | +0.0854 | +0.0546 |
| num_turns | 7.7 / 8 | 4.7 / 5 | +3 | +3 |
| duration_ms | 64690.7 / 64646 | 49933.3 / 53037 | +14757.3 | +11609 |
| input_tokens | 15.3 / 16 | 9.3 / 10 | +6 | +6 |
| output_tokens | 5028.7 / 4764 | 4378.3 / 4426 | +650.3 | +338 |
| cache_creation_input_tokens | 23101.3 / 19449 | 16066.7 / 16052 | +7034.7 | +3397 |
| cache_read_input_tokens | 239971.7 / 249370 | 159494.3 / 172337 | +80477.3 | +77033 |
| tool_errors | 0.7 / 0 | 0.3 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| one-chunk-file-per-source | 1/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
