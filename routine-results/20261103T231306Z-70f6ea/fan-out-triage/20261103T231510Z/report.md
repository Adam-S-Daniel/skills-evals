# Eval report: fan-out-triage

- Timestamp: 20261103T231510Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T231306Z-70f6ea; started 2026-11-03T23:15:10Z, ended 2026-11-03T23:16:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.79 to 0.79, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1635 / 0.1635 |
| without_skill | 1 | 0 | 1/5 | skipped (objective-decided) | 0.1004 / 0.1004 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1635 / 0.1635 | 0.1004 / 0.1004 | +0.0631 | +0.0631 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 32028 / 32028 | 27399 / 27399 | +4629 | +4629 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3315 / 3315 | 2746 / 2746 | +569 | +569 |
| cache_creation_input_tokens | 28420 / 28420 | 13104 / 13104 | +15316 | +15316 |
| cache_read_input_tokens | 166367 / 166367 | 205276 / 205276 | -38909 | -38909 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-carry-the-right-id | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
