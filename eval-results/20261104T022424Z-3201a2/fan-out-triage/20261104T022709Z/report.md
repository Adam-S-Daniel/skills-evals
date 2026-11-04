# Eval report: fan-out-triage

- Timestamp: 20261104T022709Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T022424Z-3201a2; started 2026-11-04T02:27:09Z, ended 2026-11-04T02:28:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.86 to 0.86, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 4 call(s); agent $0.24, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=1)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 1/5 | 8.8 (8.8 to 8.8, 1 judged) | 0.1545 / 0.1545 |
| without_skill | 1 | 0 | 1/5 | 6.0 (6.0 to 6.0, 1 judged) | 0.0895 / 0.0895 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1545 / 0.1545 | 0.0895 / 0.0895 | +0.0650 | +0.0650 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 31176 / 31176 | 21113 / 21113 | +10063 | +10063 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3235 / 3235 | 2257 / 2257 | +978 | +978 |
| cache_creation_input_tokens | 25548 / 25548 | 12531 / 12531 | +13017 | +13017 |
| cache_read_input_tokens | 199173 / 199173 | 167663 / 167663 | +31510 | +31510 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 0/1 | 0/1 |
| ids-match-their-source-text | 0/1 | 0/1 |
| affected-items-carry-the-right-id | 0/1 | 0/1 |
| read-count-is-the-item-count | 0/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
