# Eval report: fan-out-triage

- Timestamp: 20261107T183316Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T182630Z-4cf37f; started 2026-11-07T18:33:16Z, ended 2026-11-07T18:37:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.61, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 6 call(s); agent $0.80, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: keyword-lookalikes (n=3)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1444 / 0.4333 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.1213 / 0.3640 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1444 / 0.1339 | 0.1213 / 0.1148 | +0.0231 | +0.0190 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 39148.3 / 38893 | 35049.3 / 34905 | +4099 | +3988 |
| input_tokens | 14 / 14 | 12.7 / 12 | +1.3 | +2 |
| output_tokens | 3863.3 / 3897 | 3806.7 / 3508 | +56.7 | +389 |
| cache_creation_input_tokens | 21139.3 / 17811 | 15273.3 / 14889 | +5866 | +2922 |
| cache_read_input_tokens | 212037 / 206554 | 221336.7 / 208374 | -9299.7 | -1820 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 3/3 | 0/3 |
| results-follow-the-contract | 3/3 | 0/3 |
| ids-match-their-source-text | 3/3 | 0/3 |
| keyword-lookalikes-are-not-strong | 3/3 | 0/3 |
| strong-reasons-name-the-file | 3/3 | 0/3 |
| read-count-is-the-item-count | 3/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
