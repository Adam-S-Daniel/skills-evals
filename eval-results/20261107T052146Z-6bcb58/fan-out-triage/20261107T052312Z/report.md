# Eval report: fan-out-triage

- Timestamp: 20261107T052312Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052146Z-6bcb58; started 2026-11-07T05:23:12Z, ended 2026-11-07T05:24:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: keyword-lookalikes (n=1)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1864 / 0.1864 |
| without_skill | 1 | 0 | 1/7 | skipped (objective-decided) | 0.1148 / 0.1148 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1864 / 0.1864 | 0.1148 / 0.1148 | +0.0716 | +0.0716 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 41738 / 41738 | 34940 / 34940 | +6798 | +6798 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 4678 / 4678 | 3352 / 3352 | +1326 | +1326 |
| cache_creation_input_tokens | 29703 / 29703 | 15129 / 15129 | +14574 | +14574 |
| cache_read_input_tokens | 207795 / 207795 | 207073 / 207073 | +722 | +722 |
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
