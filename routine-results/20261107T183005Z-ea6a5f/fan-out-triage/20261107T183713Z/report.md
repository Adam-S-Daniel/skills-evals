# Eval report: fan-out-triage

- Timestamp: 20261107T183713Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183005Z-ea6a5f; started 2026-11-07T18:37:13Z, ended 2026-11-07T18:40:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 6 call(s); agent $0.70, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: shifted-draft (n=3)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/5 | skipped (objective-decided) | 0.1381 / 0.4142 |
| without_skill | 3 | 0 | 1/5 | skipped (objective-decided) | 0.0950 / 0.2849 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1381 / 0.1402 | 0.0950 / 0.0953 | +0.0431 | +0.0449 |
| num_turns | 7.3 / 8 | 5 / 5 | +2.3 | +3 |
| duration_ms | 34720.7 / 37493 | 24916.3 / 24006 | +9804.3 | +13487 |
| input_tokens | 13.3 / 14 | 10 / 10 | +3.3 | +4 |
| output_tokens | 3510.7 / 3590 | 2579.7 / 2555 | +931 | +1035 |
| cache_creation_input_tokens | 20418.3 / 18725 | 13093.7 / 13071 | +7324.7 | +5654 |
| cache_read_input_tokens | 212625.7 / 218280 | 167768.7 / 167716 | +44857 | +50564 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 2/3 | 0/3 |
| ids-match-their-source-text | 2/3 | 0/3 |
| affected-items-carry-the-right-id | 2/3 | 0/3 |
| read-count-is-the-item-count | 2/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
