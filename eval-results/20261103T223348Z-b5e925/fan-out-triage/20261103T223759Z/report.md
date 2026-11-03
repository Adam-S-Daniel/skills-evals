# Eval report: fan-out-triage

- Timestamp: 20261103T223759Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T223348Z-b5e925; started 2026-11-03T22:37:59Z, ended 2026-11-03T22:39:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.78, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: keyword-lookalikes (n=1)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1680 / 0.1680 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1272 / 0.1272 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1680 / 0.1680 | 0.1272 / 0.1272 | +0.0408 | +0.0408 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 39261 / 39261 | 47890 / 47890 | -8629 | -8629 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3955 / 3955 | 4393 / 4393 | -438 | -438 |
| cache_creation_input_tokens | 28007 / 28007 | 15655 / 15655 | +12352 | +12352 |
| cache_read_input_tokens | 164127 / 164127 | 206737 / 206737 | -42610 | -42610 |
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
