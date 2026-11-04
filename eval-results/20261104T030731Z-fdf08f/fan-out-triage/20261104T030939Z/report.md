# Eval report: fan-out-triage

- Timestamp: 20261104T030939Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T030731Z-fdf08f; started 2026-11-04T03:09:39Z, ended 2026-11-04T03:11:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: three-files (n=1)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1782 / 0.1782 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1002 / 0.1002 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1782 / 0.1782 | 0.1002 / 0.1002 | +0.0780 | +0.0780 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 79413 / 79413 | 24279 / 24279 | +55134 | +55134 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 4511 / 4511 | 2900 / 2900 | +1611 | +1611 |
| cache_creation_input_tokens | 28132 / 28132 | 14463 / 14463 | +13669 | +13669 |
| cache_read_input_tokens | 205120 / 205120 | 133063 / 133063 | +72057 | +72057 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| one-chunk-file-per-source | 0/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-found-and-decoys-not-strong | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
