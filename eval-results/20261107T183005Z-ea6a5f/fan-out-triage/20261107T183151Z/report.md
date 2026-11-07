# Eval report: fan-out-triage

- Timestamp: 20261107T183151Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183005Z-ea6a5f; started 2026-11-07T18:31:51Z, ended 2026-11-07T18:37:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.61, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.97 over 12 call(s); agent $1.37, judge $0.59, guard $0.00; last agent call $0.20

## Fixture: shifted-draft (n=3)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1/5 | 9.0 (9.0 to 9.0, 3 judged) | 0.2474 / 0.7421 |
| without_skill | 3 | 0 | 1/5 | 8.1 (7.4 to 9.0, 3 judged) | 0.2106 / 0.6317 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2474 / 0.2281 | 0.2106 / 0.2158 | +0.0368 | +0.0122 |
| num_turns | 5 / 5 | 4.7 / 5 | +0.3 | 0 |
| duration_ms | 41106.3 / 42717 | 36095.3 / 33365 | +5011 | +9352 |
| input_tokens | 10 / 10 | 9.3 / 10 | +0.7 | 0 |
| output_tokens | 3258 / 3226 | 3203.7 / 3248 | +54.3 | -22 |
| cache_creation_input_tokens | 18595.3 / 15783 | 14340.7 / 14561 | +4254.7 | +1222 |
| cache_read_input_tokens | 167029.7 / 171156 | 158588 / 171646 | +8441.7 | -490 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 0/3 | 0/3 |
| affected-items-carry-the-right-id | 0/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
