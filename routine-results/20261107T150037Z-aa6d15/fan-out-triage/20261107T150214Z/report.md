# Eval report: fan-out-triage

- Timestamp: 20261107T150214Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150037Z-aa6d15; started 2026-11-07T15:02:14Z, ended 2026-11-07T15:07:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.48, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.96 over 12 call(s); agent $1.34, judge $0.62, guard $0.00; last agent call $0.20

## Fixture: shifted-draft (n=3)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1/5 | 8.4 (7.8 to 9.0, 3 judged) | 0.2312 / 0.6935 |
| without_skill | 3 | 0 | 1/5 | 8.4 (8.4 to 8.4, 3 judged) | 0.2153 / 0.6458 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2312 / 0.2088 | 0.2153 / 0.2199 | +0.0159 | -0.0111 |
| num_turns | 4.3 / 4 | 5 / 5 | -0.7 | -1 |
| duration_ms | 38076.3 / 38134 | 36002.7 / 35635 | +2073.7 | +2499 |
| input_tokens | 8.7 / 8 | 10 / 10 | -1.3 | -2 |
| output_tokens | 3090.7 / 3070 | 3187.3 / 3215 | -96.7 | -145 |
| cache_creation_input_tokens | 17625.3 / 14178 | 14679.7 / 14803 | +2945.7 | -625 |
| cache_read_input_tokens | 141499.7 / 131803 | 170282 / 170064 | -28782.3 | -38261 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 0/3 | 0/3 |
| affected-items-carry-the-right-id | 0/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
