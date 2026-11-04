# Eval report: fan-out-triage

- Timestamp: 20261104T004127Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T003954Z-0a3398; started 2026-11-04T00:41:27Z, ended 2026-11-04T00:42:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: three-files (n=1)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1783 / 0.1783 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.0876 / 0.0876 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1783 / 0.1783 | 0.0876 / 0.0876 | +0.0907 | +0.0907 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 35294 / 35294 | 21145 / 21145 | +14149 | +14149 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4508 / 4508 | 2309 / 2309 | +2199 | +2199 |
| cache_creation_input_tokens | 29190 / 29190 | 12839 / 12839 | +16351 | +16351 |
| cache_read_input_tokens | 164320 / 164320 | 131437 / 131437 | +32883 | +32883 |
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
