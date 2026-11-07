# Eval report: fan-out-triage

- Timestamp: 20261107T105057Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T104923Z-cbe74d; started 2026-11-07T10:50:57Z, ended 2026-11-07T10:52:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.4, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 4 call(s); agent $0.44, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: shifted-draft (n=2)

- Prompt: A teammate started triaging the acme 2.x release notes excerpt in notes/ against this repo; their draft is triage/draft.tsv. Finish the job and put the final triage in triage/results.tsv. I plan to paste item text into issues straight from your file, so it has to be right.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 3/5 | skipped (objective-decided) | 0.1294 / 0.2588 |
| without_skill | 2 | 0 | 1/5 | skipped (objective-decided) | 0.0910 / 0.1821 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1294 / 0.1294 | 0.0910 / 0.0910 | +0.0384 | +0.0384 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 29546.5 / 29546.5 | 22452.5 / 22452.5 | +7094 | +7094 |
| input_tokens | 11 / 11 | 10 / 10 | +1 | +1 |
| output_tokens | 3036.5 / 3036.5 | 2286.5 / 2286.5 | +750 | +750 |
| cache_creation_input_tokens | 20556 / 20556 | 12841.5 / 12841.5 | +7714.5 | +7714.5 |
| cache_read_input_tokens | 168004.5 / 168004.5 | 167810.5 / 167810.5 | +194 | +194 |
| tool_errors | 0 / 0 | 0.5 / 0.5 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| results-follow-the-contract | 1/2 | 0/2 |
| ids-match-their-source-text | 1/2 | 0/2 |
| affected-items-carry-the-right-id | 1/2 | 0/2 |
| read-count-is-the-item-count | 1/2 | 0/2 |
| repo-and-notes-untouched | 2/2 | 2/2 |
