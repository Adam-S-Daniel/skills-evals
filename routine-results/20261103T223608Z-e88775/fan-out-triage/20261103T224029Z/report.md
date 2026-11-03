# Eval report: fan-out-triage

- Timestamp: 20261103T224029Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T223608Z-e88775; started 2026-11-03T22:40:29Z, ended 2026-11-03T22:41:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: single-file (n=1)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1683 / 0.1683 |
| without_skill | 1 | 0 | 1/6 | skipped (objective-decided) | 0.1113 / 0.1113 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1683 / 0.1683 | 0.1113 / 0.1113 | +0.0570 | +0.0570 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 34923 / 34923 | 38583 / 38583 | -3660 | -3660 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3510 / 3510 | 3087 / 3087 | +423 | +423 |
| cache_creation_input_tokens | 28167 / 28167 | 14820 / 14820 | +13347 | +13347 |
| cache_read_input_tokens | 205127 / 205127 | 211108 / 211108 | -5981 | -5981 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-found-and-decoys-not-strong | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
