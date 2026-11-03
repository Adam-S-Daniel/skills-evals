# Eval report: writing-adrs

- Timestamp: 20261103T161429Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T161247Z-2155b6; started 2026-11-03T16:14:29Z, ended 2026-11-03T16:16:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.68 over 4 call(s); agent $0.66, judge $1.02, guard $0.00; last agent call $0.33

## Fixture: existing-convention (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.1 (9.1 to 9.1, 1 judged) | 0.3306 / 0.3306 |
| without_skill | 1 | 0 | 7/7 | 9.1 (9.1 to 9.1, 1 judged) | 0.3282 / 0.3282 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3306 / 0.3306 | 0.3282 / 0.3282 | +0.0024 | +0.0024 |
| num_turns | 7 / 7 | 9 / 9 | -2 | -2 |
| duration_ms | 33682 / 33682 | 39352 / 39352 | -5670 | -5670 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 3163 / 3163 | 3478 / 3478 | -315 | -315 |
| cache_creation_input_tokens | 29092 / 29092 | 26296 / 26296 | +2796 | +2796 |
| cache_read_input_tokens | 172965 / 172965 | 241214 / 241214 | -68249 | -68249 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 1/1 | 1/1 |
| index-gained-a-row-for-0004 | 1/1 | 1/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-new-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
