# Eval report: fan-out-triage

- Timestamp: 20261103T043027Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T042840Z-ec9223; started 2026-11-03T04:30:27Z, ended 2026-11-03T04:32:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1734 / 0.1734 |
| without_skill | 1 | 0 | 1/5 | skipped (objective-decided) | 0.0937 / 0.0937 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1734 / 0.1734 | 0.0937 / 0.0937 | +0.0797 | +0.0797 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 66459 / 66459 | 23904 / 23904 | +42555 | +42555 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 3651 / 3651 | 2471 / 2471 | +1180 | +1180 |
| cache_creation_input_tokens | 28082 / 28082 | 13066 / 13066 | +15016 | +15016 |
| cache_read_input_tokens | 245393 / 245393 | 167440 / 167440 | +77953 | +77953 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-carry-the-right-id | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
