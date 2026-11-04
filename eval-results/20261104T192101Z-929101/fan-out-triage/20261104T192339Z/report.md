# Eval report: fan-out-triage

- Timestamp: 20261104T192339Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T192101Z-929101; started 2026-11-04T19:23:39Z, ended 2026-11-04T19:25:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: keyword-lookalikes (n=1)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1857 / 0.1857 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1276 / 0.1276 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1857 / 0.1857 | 0.1276 / 0.1276 | +0.0581 | +0.0581 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 70784 / 70784 | 52527 / 52527 | +18257 | +18257 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 4395 / 4395 | 4321 / 4321 | +74 | +74 |
| cache_creation_input_tokens | 29263 / 29263 | 15911 / 15911 | +13352 | +13352 |
| cache_read_input_tokens | 246211 / 246211 | 206812 / 206812 | +39399 | +39399 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| keyword-lookalikes-are-not-strong | 1/1 | 0/1 |
| strong-reasons-name-the-file | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
