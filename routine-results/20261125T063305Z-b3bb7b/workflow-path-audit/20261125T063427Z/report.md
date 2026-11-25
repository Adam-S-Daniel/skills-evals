# Eval report: workflow-path-audit

- Timestamp: 20261125T063427Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T063305Z-b3bb7b; started 2026-11-25T06:34:27Z, ended 2026-11-25T06:35:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 2 call(s); agent $0.33, judge $0.00, guard $0.00; last agent call $0.16
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.03); Fable meter 0.00 points

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | skipped: the version with the skill passed more checks (6 of 10 vs 5 of 10) | 0.1682 / 0.1682 |
| without_skill | 1 | 0 | 5/10 | skipped: the version with the skill passed more checks (6 of 10 vs 5 of 10) | 0.1594 / 0.1594 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1682 / 0.1682 | 0.1594 / 0.1594 | +0.0088 | +0.0088 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 31855 / 31855 | 31655 / 31655 | +200 | +200 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3576 / 3576 | 3975 / 3975 | -399 | -399 |
| cache_creation_input_tokens | 26948 / 26948 | 25798 / 25798 | +1150 | +1150 |
| cache_read_input_tokens | 246248 / 246248 | 164791 / 164791 | +81457 | +81457 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 0/1 |
| source-change-runs-only-the-tests | 0/1 | 0/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 0/1 |
| agents-md-change-runs-nothing | 0/1 | 0/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 0/1 |
