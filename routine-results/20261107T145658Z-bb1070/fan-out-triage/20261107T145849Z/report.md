# Eval report: fan-out-triage

- Timestamp: 20261107T145849Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T145658Z-bb1070; started 2026-11-07T14:58:49Z, ended 2026-11-07T15:04:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.48, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.73 over 6 call(s); agent $1.73, judge $0.00, guard $0.00; last agent call $0.27

## Fixture: keyword-lookalikes (n=3)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/7 | skipped (objective-decided) | 0.2973 / 0.8919 |
| without_skill | 3 | 0 | 1/7 | skipped (objective-decided) | 0.2782 / 0.8346 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2973 / 0.2976 | 0.2782 / 0.2651 | +0.0191 | +0.0324 |
| num_turns | 6.7 / 7 | 7 / 7 | -0.3 | 0 |
| duration_ms | 50521 / 53233 | 56311 / 59381 | -5790 | -6148 |
| input_tokens | 12.7 / 14 | 14 / 14 | -1.3 | 0 |
| output_tokens | 4457.7 / 4807 | 4638.3 / 4270 | -180.7 | +537 |
| cache_creation_input_tokens | 20727.3 / 19653 | 16907.3 / 16385 | +3820 | +3268 |
| cache_read_input_tokens | 211426.7 / 220724 | 250628.7 / 249148 | -39202 | -28424 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/3 | 0/3 |
| results-follow-the-contract | 1/3 | 0/3 |
| ids-match-their-source-text | 1/3 | 0/3 |
| keyword-lookalikes-are-not-strong | 1/3 | 0/3 |
| strong-reasons-name-the-file | 1/3 | 0/3 |
| read-count-is-the-item-count | 1/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
