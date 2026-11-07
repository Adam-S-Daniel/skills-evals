# Eval report: fan-out-triage

- Timestamp: 20261107T151415Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150413Z-01f684; started 2026-11-07T15:14:15Z, ended 2026-11-07T15:18:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 6 call(s); agent $0.72, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: single-file (n=3)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.1386 / 0.4157 |
| without_skill | 3 | 0 | 1/6 | skipped (objective-decided) | 0.1014 / 0.3041 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1386 / 0.1345 | 0.1014 / 0.1009 | +0.0372 | +0.0336 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 46700 / 47465 | 37279 / 33134 | +9421 | +14331 |
| input_tokens | 14.7 / 14 | 8.7 / 8 | +6 | +6 |
| output_tokens | 3716.3 / 3595 | 3179 / 2885 | +537.3 | +710 |
| cache_creation_input_tokens | 19790.7 / 17044 | 13787 / 13776 | +6003.7 | +3268 |
| cache_read_input_tokens | 222005.3 / 210026 | 144278 / 132216 | +77727.3 | +77810 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
