# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T055013Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T054847Z-9ffe54; started 2026-11-07T05:50:13Z, ended 2026-11-07T05:51:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 4 call(s); agent $0.22, judge $0.06, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.1334 / 0.1334 |
| without_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.0902 / 0.0902 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1334 / 0.1334 | 0.0902 / 0.0902 | +0.0432 | +0.0432 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 16445 / 16445 | 15878 / 15878 | +567 | +567 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1525 / 1525 | 1592 / 1592 | -67 | -67 |
| cache_creation_input_tokens | 25358 / 25358 | 14154 / 14154 | +11204 | +11204 |
| cache_read_input_tokens | 166588 / 166588 | 176424 / 176424 | -9836 | -9836 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
