# Eval report: fan-out-triage

- Timestamp: 20261107T093228Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T093133Z-9d1caa; started 2026-11-07T09:32:28Z, ended 2026-11-07T09:34:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.37, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 6 call(s); agent $0.25, judge $0.12, guard $0.00; last agent call $0.08

## Fixture: shifted-draft (n=3)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 1/5 | 7.4 (7.2 to 7.8, 3 judged) | 0.0846 / 0.2538 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0846 / 0.0861 |
| num_turns | 4.7 / 5 |
| duration_ms | 28443 / 24368 |
| input_tokens | 9.3 / 10 |
| output_tokens | 2245.3 / 2319 |
| cache_creation_input_tokens | 11399.7 / 11268 |
| cache_read_input_tokens | 165383.7 / 177745 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| results-follow-the-contract | 0/3 |
| ids-match-their-source-text | 0/3 |
| affected-items-carry-the-right-id | 0/3 |
| read-count-is-the-item-count | 0/3 |
| repo-and-notes-untouched | 3/3 |
