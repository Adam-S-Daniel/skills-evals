# Eval report: workflow-path-audit

- Timestamp: 20261125T065849Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T065722Z-2b0eab; started 2026-11-25T06:58:49Z, ended 2026-11-25T07:00:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.29, judge $0.08, guard $0.00; last agent call $0.14
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 5.5 (5.5 to 5.5, 1 judged) | 0.1495 / 0.1495 |
| without_skill | 1 | 0 | 10/10 | 10.0 (10.0 to 10.0, 1 judged) | 0.1432 / 0.1432 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1495 / 0.1495 | 0.1432 / 0.1432 | +0.0063 | +0.0063 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 26560 / 26560 | 23567 / 23567 | +2993 | +2993 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3018 / 3018 | 2131 / 2131 | +887 | +887 |
| cache_creation_input_tokens | 25700 / 25700 | 25344 / 25344 | +356 | +356 |
| cache_read_input_tokens | 165305 / 165305 | 204783 / 204783 | -39478 | -39478 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 1/1 |
| source-change-runs-only-the-tests | 0/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 1/1 |
| agents-md-change-runs-nothing | 0/1 | 1/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
