# Eval report: fan-out-triage

- Timestamp: 20261107T105427Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T105254Z-e7d3c3; started 2026-11-07T10:54:27Z, ended 2026-11-07T10:56:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.41, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 4 call(s); agent $0.50, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: single-file (n=2)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 6/6 | skipped (objective-decided) | 0.1380 / 0.2761 |
| without_skill | 2 | 0 | 1/6 | skipped (objective-decided) | 0.1101 / 0.2201 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1380 / 0.1380 | 0.1101 / 0.1101 | +0.0280 | +0.0280 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 35885 / 35885 | 29409.5 / 29409.5 | +6475.5 | +6475.5 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3446.5 / 3446.5 | 3055.5 / 3055.5 | +391 | +391 |
| cache_creation_input_tokens | 21645.5 / 21645.5 | 15588 / 15588 | +6057.5 | +6057.5 |
| cache_read_input_tokens | 169579.5 / 169579.5 | 171473.5 / 171473.5 | -1894 | -1894 |
| tool_errors | 0 / 0 | 0.5 / 0.5 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 2/2 | 0/2 |
| results-follow-the-contract | 2/2 | 0/2 |
| ids-match-their-source-text | 2/2 | 0/2 |
| affected-items-found-and-decoys-not-strong | 2/2 | 0/2 |
| read-count-is-the-item-count | 2/2 | 0/2 |
| repo-and-notes-untouched | 2/2 | 2/2 |
