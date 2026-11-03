# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T092036Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T091843Z-1917d5; started 2026-11-03T09:20:36Z, ended 2026-11-03T09:23:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.22 over 4 call(s); agent $0.80, judge $0.42, guard $0.00; last agent call $0.39

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 8.0 (8.0 to 8.0, 1 judged) | 0.4062 / 0.4062 |
| without_skill | 1 | 0 | 2/3 | 7.8 (7.8 to 7.8, 1 judged) | 0.3940 / 0.3940 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4062 / 0.4062 | 0.3940 / 0.3940 | +0.0122 | +0.0122 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 75134 / 75134 | 66062 / 66062 | +9072 | +9072 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 4516 / 4516 | 3529 / 3529 | +987 | +987 |
| cache_creation_input_tokens | 30823 / 30823 | 18928 / 18928 | +11895 | +11895 |
| cache_read_input_tokens | 297126 / 297126 | 221241 / 221241 | +75885 | +75885 |
| tool_errors | 2 / 2 | 3 / 3 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
