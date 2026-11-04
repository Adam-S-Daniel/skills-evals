# Eval report: fan-out-triage

- Timestamp: 20261104T001846Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T001651Z-2f6d38; started 2026-11-04T00:18:46Z, ended 2026-11-04T00:20:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.82 to 0.82, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: single-file (n=1)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1492 / 0.1492 |
| without_skill | 1 | 0 | 1/6 | skipped (objective-decided) | 0.0907 / 0.0907 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1492 / 0.1492 | 0.0907 / 0.0907 | +0.0585 | +0.0585 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 60978 / 60978 | 24511 / 24511 | +36467 | +36467 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3370 / 3370 | 2477 / 2477 | +893 | +893 |
| cache_creation_input_tokens | 25770 / 25770 | 13198 / 13198 | +12572 | +12572 |
| cache_read_input_tokens | 123811 / 123811 | 131321 / 131321 | -7510 | -7510 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/1 | 0/1 |
| results-follow-the-contract | 1/1 | 0/1 |
| ids-match-their-source-text | 1/1 | 0/1 |
| affected-items-found-and-decoys-not-strong | 1/1 | 0/1 |
| read-count-is-the-item-count | 1/1 | 0/1 |
| repo-and-notes-untouched | 1/1 | 1/1 |
