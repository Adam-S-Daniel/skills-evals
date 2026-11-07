# Eval report: fan-out-triage

- Timestamp: 20261107T151531Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150747Z-342890; started 2026-11-07T15:15:31Z, ended 2026-11-07T15:20:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 6 call(s); agent $0.82, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1628 / 0.4885 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.1104 / 0.3311 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1628 / 0.1537 | 0.1104 / 0.1058 | +0.0525 | +0.0479 |
| num_turns | 8 / 8 | 4.7 / 4 | +3.3 | +4 |
| duration_ms | 57248 / 54108 | 34130 / 35421 | +23118 | +18687 |
| input_tokens | 14 / 14 | 8.7 / 8 | +5.3 | +6 |
| output_tokens | 5116 / 5188 | 3544.7 / 3537 | +1571.3 | +1651 |
| cache_creation_input_tokens | 22580.7 / 20509 | 15066 / 14578 | +7514.7 | +5931 |
| cache_read_input_tokens | 213349.3 / 213175 | 146538.3 / 133636 | +66811 | +79539 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| one-chunk-file-per-source | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
