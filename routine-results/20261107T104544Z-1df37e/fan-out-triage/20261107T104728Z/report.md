# Eval report: fan-out-triage

- Timestamp: 20261107T104728Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T104544Z-1df37e; started 2026-11-07T10:47:28Z, ended 2026-11-07T10:50:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.4, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 4 call(s); agent $0.53, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: keyword-lookalikes (n=2)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1484 / 0.2968 |
| without_skill | 2 | 0 | 1/7 | skipped (objective-decided) | 0.1184 / 0.2368 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1484 / 0.1484 | 0.1184 / 0.1184 | +0.0300 | +0.0300 |
| num_turns | 8 / 8 | 6.5 / 6.5 | +1.5 | +1.5 |
| duration_ms | 34432 / 34432 | 38180.5 / 38180.5 | -3748.5 | -3748.5 |
| input_tokens | 15 / 15 | 13 / 13 | +2 | +2 |
| output_tokens | 3741 / 3741 | 3737 / 3737 | +4 | +4 |
| cache_creation_input_tokens | 22045 / 22045 | 14634 / 14634 | +7411 | +7411 |
| cache_read_input_tokens | 227552.5 / 227552.5 | 224708.5 / 224708.5 | +2844 | +2844 |
| tool_errors | 0 / 0 | 0.5 / 0.5 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 2/2 | 0/2 |
| results-follow-the-contract | 2/2 | 0/2 |
| ids-match-their-source-text | 2/2 | 0/2 |
| keyword-lookalikes-are-not-strong | 2/2 | 0/2 |
| strong-reasons-name-the-file | 2/2 | 0/2 |
| read-count-is-the-item-count | 2/2 | 0/2 |
| repo-and-notes-untouched | 2/2 | 2/2 |
