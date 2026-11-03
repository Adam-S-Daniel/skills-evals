# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T204154Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T201310Z-d49826; started 2026-11-03T20:41:54Z, ended 2026-11-03T20:44:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 4 call(s); agent $0.71, judge $0.40, guard $0.00; last agent call $0.32

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.3952 / 0.3952 |
| without_skill | 1 | 0 | 2/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.3151 / 0.3151 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3952 / 0.3952 | 0.3151 / 0.3151 | +0.0801 | +0.0801 |
| num_turns | 6 / 6 | 8 / 8 | -2 | -2 |
| duration_ms | 69543 / 69543 | 74570 / 74570 | -5027 | -5027 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 4947 / 4947 | 4608 / 4608 | +339 | +339 |
| cache_creation_input_tokens | 30783 / 30783 | 19431 / 19431 | +11352 | +11352 |
| cache_read_input_tokens | 211904 / 211904 | 306759 / 306759 | -94855 | -94855 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
