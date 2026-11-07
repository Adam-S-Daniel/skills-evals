# Eval report: fan-out-triage

- Timestamp: 20261107T104347Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T104210Z-5129c7; started 2026-11-07T10:43:47Z, ended 2026-11-07T10:45:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 4 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: three-files (n=2)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1858 / 0.3716 |
| without_skill | 2 | 0 | 1/7 | skipped (objective-decided) | 0.0912 / 0.1824 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1858 / 0.1858 | 0.0912 / 0.0912 | +0.0946 | +0.0946 |
| num_turns | 7.5 / 7.5 | 4 / 4 | +3.5 | +3.5 |
| duration_ms | 37613 / 37613 | 23700.5 / 23700.5 | +13912.5 | +13912.5 |
| input_tokens | 13 / 13 | 8 / 8 | +5 | +5 |
| output_tokens | 4430 / 4430 | 2383.5 / 2383.5 | +2046.5 | +2046.5 |
| cache_creation_input_tokens | 30732 / 30732 | 13534 / 13534 | +17198 | +17198 |
| cache_read_input_tokens | 185324 / 185324 | 132351.5 / 132351.5 | +52972.5 | +52972.5 |
| tool_errors | 0.5 / 0.5 | 0.5 / 0.5 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 2/2 | 0/2 |
| one-chunk-file-per-source | 2/2 | 0/2 |
| results-follow-the-contract | 2/2 | 0/2 |
| ids-match-their-source-text | 2/2 | 0/2 |
| affected-items-found-and-decoys-not-strong | 2/2 | 0/2 |
| read-count-is-the-item-count | 2/2 | 0/2 |
| repo-and-notes-untouched | 2/2 | 2/2 |
