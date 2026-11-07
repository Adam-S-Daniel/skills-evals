# Eval report: fan-out-triage

- Timestamp: 20261107T150732Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150037Z-aa6d15; started 2026-11-07T15:07:32Z, ended 2026-11-07T15:11:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 6 call(s); agent $0.69, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=3)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2.3/5 | skipped (objective-decided) | 0.1333 / 0.3998 |
| without_skill | 3 | 0 | 1/5 | skipped (objective-decided) | 0.0960 / 0.2881 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1333 / 0.1366 | 0.0960 / 0.0940 | +0.0372 | +0.0426 |
| num_turns | 6.3 / 6 | 5.3 / 5 | +1 | +1 |
| duration_ms | 36113 / 37608 | 31647.7 / 31359 | +4465.3 | +6249 |
| input_tokens | 12 / 12 | 10.7 / 10 | +1.3 | +2 |
| output_tokens | 3455.7 / 3651 | 2523.7 / 2541 | +932 | +1110 |
| cache_creation_input_tokens | 19733.3 / 19151 | 13193.3 / 12926 | +6540 | +6225 |
| cache_read_input_tokens | 197572.3 / 211205 | 180016 / 167726 | +17556.3 | +43479 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/3 | 0/3 |
| ids-match-their-source-text | 1/3 | 0/3 |
| affected-items-carry-the-right-id | 1/3 | 0/3 |
| read-count-is-the-item-count | 1/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
