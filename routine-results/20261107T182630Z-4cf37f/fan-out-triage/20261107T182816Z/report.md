# Eval report: fan-out-triage

- Timestamp: 20261107T182816Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T182630Z-4cf37f; started 2026-11-07T18:28:16Z, ended 2026-11-07T18:33:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.68 over 6 call(s); agent $1.68, judge $0.00, guard $0.00; last agent call $0.25

## Fixture: keyword-lookalikes (n=3)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/7 | skipped (objective-decided) | 0.3070 / 0.9211 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.2524 / 0.7572 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3070 / 0.2959 | 0.2524 / 0.2533 | +0.0546 | +0.0426 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 48353.3 / 46192 | 47128.3 / 41891 | +1225 | +4301 |
| input_tokens | 13.3 / 14 | 11.3 / 12 | +2 | +2 |
| output_tokens | 4641.3 / 4674 | 4221.3 / 3965 | +420 | +709 |
| cache_creation_input_tokens | 21133.3 / 19743 | 16000.7 / 16382 | +5132.7 | +3361 |
| cache_read_input_tokens | 225456.3 / 221987 | 199590.7 / 212535 | +25865.7 | +9452 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/3 | 0/3 |
| results-follow-the-contract | 1/3 | 0/3 |
| ids-match-their-source-text | 1/3 | 0/3 |
| keyword-lookalikes-are-not-strong | 1/3 | 0/3 |
| strong-reasons-name-the-file | 1/3 | 0/3 |
| read-count-is-the-item-count | 1/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
