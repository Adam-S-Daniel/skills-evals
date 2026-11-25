# Eval report: workflow-path-audit

- Timestamp: 20261125T085909Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T085740Z-f9e89a; started 2026-11-25T08:59:09Z, ended 2026-11-25T09:00:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.14
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | skipped: the version with the skill passed more checks (10 of 10 vs 6 of 10) | 0.1605 / 0.1605 |
| without_skill | 1 | 0 | 6/10 | skipped: the version with the skill passed more checks (10 of 10 vs 6 of 10) | 0.1432 / 0.1432 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1605 / 0.1605 | 0.1432 / 0.1432 | +0.0173 | +0.0173 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 26676 / 26676 | 24095 / 24095 | +2581 | +2581 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 2613 / 2613 | 2746 / 2746 | -133 | -133 |
| cache_creation_input_tokens | 26465 / 26465 | 24815 / 24815 | +1650 | +1650 |
| cache_read_input_tokens | 284888 / 284888 | 164738 / 164738 | +120150 | +120150 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 1/1 | 0/1 |
| source-change-runs-only-the-tests | 1/1 | 0/1 |
| lockfile-change-runs-only-the-tests | 1/1 | 0/1 |
| agents-md-change-runs-nothing | 1/1 | 0/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
