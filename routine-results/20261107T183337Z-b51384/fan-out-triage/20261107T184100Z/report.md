# Eval report: fan-out-triage

- Timestamp: 20261107T184100Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183337Z-b51384; started 2026-11-07T18:41:00Z, ended 2026-11-07T18:45:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.77 over 6 call(s); agent $0.77, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: single-file (n=3)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.1380 / 0.4141 |
| without_skill | 3 | 0 | 1/6 | skipped (objective-decided) | 0.1182 / 0.3545 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1380 / 0.1252 | 0.1182 / 0.1043 | +0.0199 | +0.0209 |
| num_turns | 7.7 / 8 | 6.3 / 6 | +1.3 | +2 |
| duration_ms | 43992.7 / 40980 | 32804.3 / 29548 | +11188.3 | +11432 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3614.3 / 3624 | 3205.3 / 2982 | +409 | +642 |
| cache_creation_input_tokens | 20251.3 / 16899 | 16256.7 / 13482 | +3994.7 | +3417 |
| cache_read_input_tokens | 208538 / 212194 | 210541 / 205394 | -2003 | +6800 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
