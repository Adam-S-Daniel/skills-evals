# Eval report: fan-out-triage

- Timestamp: 20261107T052206Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052031Z-6bcdfb; started 2026-11-07T05:22:06Z, ended 2026-11-07T05:23:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: three-files (n=1)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.2015 / 0.2015 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.0855 / 0.0855 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2015 / 0.2015 | 0.0855 / 0.0855 | +0.1160 | +0.1160 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 54219 / 54219 | 23476 / 23476 | +30743 | +30743 |
| input_tokens | 16 / 16 | 8 / 8 | +8 | +8 |
| output_tokens | 5468 / 5468 | 2070 / 2070 | +3398 | +3398 |
| cache_creation_input_tokens | 30538 / 30538 | 12909 / 12909 | +17629 | +17629 |
| cache_read_input_tokens | 246365 / 246365 | 131314 / 131314 | +115051 | +115051 |
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
