# Eval report: fan-out-triage

- Timestamp: 20261107T054300Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T054127Z-aabc1e; started 2026-11-07T05:43:00Z, ended 2026-11-07T05:44:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.24, judge $0.08, guard $0.00; last agent call $0.10

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 1/5 | 5.8 (5.8 to 5.8, 1 judged) | 0.1479 / 0.1479 |
| without_skill | 1 | 0 | 1/5 | 5.4 (5.4 to 5.4, 1 judged) | 0.0961 / 0.0961 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1479 / 0.1479 | 0.0961 / 0.0961 | +0.0517 | +0.0517 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 29569 / 29569 | 26648 / 26648 | +2921 | +2921 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3139 / 3139 | 2319 / 2319 | +820 | +820 |
| cache_creation_input_tokens | 25116 / 25116 | 13119 / 13119 | +11997 | +11997 |
| cache_read_input_tokens | 159835 / 159835 | 204301 / 204301 | -44466 | -44466 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 0/1 | 0/1 |
| ids-match-their-source-text | 0/1 | 0/1 |
| affected-items-carry-the-right-id | 0/1 | 0/1 |
| read-count-is-the-item-count | 0/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
