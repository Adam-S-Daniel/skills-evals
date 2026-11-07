# Eval report: fan-out-triage

- Timestamp: 20261107T045843Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T045707Z-4312d6; started 2026-11-07T04:58:43Z, ended 2026-11-07T04:59:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1722 / 0.1722 |
| without_skill | 1 | 0 | 1/5 | skipped (objective-decided) | 0.0918 / 0.0918 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1722 / 0.1722 | 0.0918 / 0.0918 | +0.0804 | +0.0804 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 45681 / 45681 | 25899 / 25899 | +19782 | +19782 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4050 / 4050 | 2445 / 2445 | +1605 | +1605 |
| cache_creation_input_tokens | 27822 / 27822 | 12628 / 12628 | +15194 | +15194 |
| cache_read_input_tokens | 203458 / 203458 | 168132 / 168132 | +35326 | +35326 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-carry-the-right-id | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
