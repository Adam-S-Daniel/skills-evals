# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T214513Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T213505Z-eb0d34; started 2026-11-03T21:45:13Z, ended 2026-11-03T21:48:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.24 over 4 call(s); agent $0.81, judge $0.43, guard $0.00; last agent call $0.31

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 8.0 (8.0 to 8.0, 1 judged) | 0.5036 / 0.5036 |
| without_skill | 1 | 0 | 2/3 | 7.8 (7.8 to 7.8, 1 judged) | 0.3099 / 0.3099 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5036 / 0.5036 | 0.3099 / 0.3099 | +0.1936 | +0.1936 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 67098 / 67098 | 84394 / 84394 | -17296 | -17296 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 4165 / 4165 | 4863 / 4863 | -698 | -698 |
| cache_creation_input_tokens | 30301 / 30301 | 19036 / 19036 | +11265 | +11265 |
| cache_read_input_tokens | 212592 / 212592 | 265179 / 265179 | -52587 | -52587 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
