# Eval report: fan-out-triage

- Timestamp: 20261107T184441Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183710Z-0eaa74; started 2026-11-07T18:44:41Z, ended 2026-11-07T18:48:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 6 call(s); agent $0.81, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: three-files (n=3)

- Prompt: We just upgraded the acme CLI across three minor versions and the release notes are in notes/ (one file per version). Work out which items affect this repo and where. Use triage/ for working files and write the combined result to triage/results.tsv. It is a lot of text, so split it up however makes sense, and I want to be able to check each answer against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1552 / 0.4655 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.1142 / 0.3425 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1552 / 0.1321 | 0.1142 / 0.1157 | +0.0410 | +0.0164 |
| num_turns | 7.7 / 7 | 4.7 / 5 | +3 | +2 |
| duration_ms | 44209.7 / 42066 | 33035 / 30900 | +11174.7 | +11166 |
| input_tokens | 13.3 / 12 | 9.3 / 10 | +4 | +2 |
| output_tokens | 4595.7 / 4171 | 3649.3 / 3707 | +946.3 | +464 |
| cache_creation_input_tokens | 22257.7 / 18162 | 15430.3 / 15397 | +6827.3 | +2765 |
| cache_read_input_tokens | 201379 / 176747 | 159226.7 / 171077 | +42152.3 | +5670 |
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
