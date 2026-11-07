# Eval report: fan-out-triage

- Timestamp: 20261107T052049Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051922Z-497d5d; started 2026-11-07T05:20:49Z, ended 2026-11-07T05:22:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: single-file (n=1)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1605 / 0.1605 |
| without_skill | 1 | 0 | 1/6 | skipped (objective-decided) | 0.1052 / 0.1052 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1605 / 0.1605 | 0.1052 / 0.1052 | +0.0553 | +0.0553 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 35364 / 35364 | 31226 / 31226 | +4138 | +4138 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3586 / 3586 | 3235 / 3235 | +351 | +351 |
| cache_creation_input_tokens | 27091 / 27091 | 14013 / 14013 | +13078 | +13078 |
| cache_read_input_tokens | 162118 / 162118 | 167815 / 167815 | -5697 | -5697 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-found-and-decoys-not-strong | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
