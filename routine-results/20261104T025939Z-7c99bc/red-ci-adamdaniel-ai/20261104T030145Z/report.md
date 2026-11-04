# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261104T030145Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T025939Z-7c99bc; started 2026-11-04T03:01:45Z, ended 2026-11-04T03:02:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.1334 / 0.1334 |
| without_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.0893 / 0.0893 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1334 / 0.1334 | 0.0893 / 0.0893 | +0.0441 | +0.0441 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 19222 / 19222 | 19071 / 19071 | +151 | +151 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1676 / 1676 | 1485 / 1485 | +191 | +191 |
| cache_creation_input_tokens | 24979 / 24979 | 14187 / 14187 | +10792 | +10792 |
| cache_read_input_tokens | 167156 / 167156 | 176832 / 176832 | -9676 | -9676 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
