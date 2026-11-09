# Eval report: fan-out-triage

- Timestamp: 20261109T173657Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T173251Z-e916ea; started 2026-11-09T17:36:57Z, ended 2026-11-09T17:38:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 6 call(s); agent $0.23, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: keyword-lookalikes (n=3)

- Prompt: Here are the keyword-heavy acme release notes in notes/. Plenty of them mention commands we use, but I only care about the ones that change something we rely on. Work out which ones and where, keeping working files in triage/ and the final answer in triage/results.tsv. I will quote items from your file in tickets, so I need to be able to trust each line.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/7 | 6.0 (6.0 to 6.0, 3 judged) | 0.0762 / 0.2286 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0762 / 0.0758 |
| num_turns | 6.3 / 6 |
| duration_ms | 23927 / 22480 |
| input_tokens | 12.7 / 12 |
| output_tokens | 2464 / 2478 |
| cache_creation_input_tokens | 11447.7 / 11314 |
| cache_read_input_tokens | 229019.3 / 215915 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| inventory-cites-real-lines | 0/3 |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| keyword-lookalikes-are-not-strong | 0/3 |
| strong-reasons-name-the-file | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
