# Eval report: fan-out-triage

- Timestamp: 20261107T080702Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T080540Z-26eb83; started 2026-11-07T08:07:02Z, ended 2026-11-07T08:08:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.24, judge $0.07, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 1/5 | 6.0 (6.0 to 6.0, 1 judged) | 0.1516 / 0.1516 |
| without_skill | 1 | 0 | 1/5 | 5.0 (5.0 to 5.0, 1 judged) | 0.0890 / 0.0890 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1516 / 0.1516 | 0.0890 / 0.0890 | +0.0626 | +0.0626 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 29859 / 29859 | 22344 / 22344 | +7515 | +7515 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3166 / 3166 | 2237 / 2237 | +929 | +929 |
| cache_creation_input_tokens | 25970 / 25970 | 12483 / 12483 | +13487 | +13487 |
| cache_read_input_tokens | 160515 / 160515 | 167139 / 167139 | -6624 | -6624 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 0/1 | 0/1 |
| ids-match-their-source-text | 0/1 | 0/1 |
| affected-items-carry-the-right-id | 0/1 | 0/1 |
| read-count-is-the-item-count | 0/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
