# Eval report: fan-out-triage

- Timestamp: 20261104T185857Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T185701Z-ff7b56; started 2026-11-04T18:58:57Z, ended 2026-11-04T19:00:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.1812 / 0.1812 |
| without_skill | 1 | 0 | 1/5 | skipped (objective-decided) | 0.0924 / 0.0924 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1812 / 0.1812 | 0.0924 / 0.0924 | +0.0888 | +0.0888 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 58688 / 58688 | 34582 / 34582 | +24106 | +24106 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 3958 / 3958 | 2438 / 2438 | +1520 | +1520 |
| cache_creation_input_tokens | 29176 / 29176 | 12810 / 12810 | +16366 | +16366 |
| cache_read_input_tokens | 249259 / 249259 | 167546 / 167546 | +81713 | +81713 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-carry-the-right-id | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
