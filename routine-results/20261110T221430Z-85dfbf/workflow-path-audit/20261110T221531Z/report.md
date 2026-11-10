# Eval report: workflow-path-audit

- Timestamp: 20261110T221531Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T221430Z-85dfbf; started 2026-11-10T22:15:31Z, ended 2026-11-10T22:16:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 6 call(s); agent $0.54, judge $0.16, guard $0.00; last agent call $0.14

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 10/10 | 9.9 (9.8 to 10.0, 3 judged) | 0.1787 / 0.5362 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1787 / 0.1352 |
| num_turns | 4.3 / 4 |
| duration_ms | 19155.3 / 19179 |
| input_tokens | 8.7 / 8 |
| output_tokens | 1712.3 / 1732 |
| cache_creation_input_tokens | 22905.7 / 14211 |
| cache_read_input_tokens | 149555.7 / 147301 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| docs-change-builds-only-the-docs | 3/3 |
| source-change-runs-only-the-tests | 3/3 |
| lockfile-change-runs-only-the-tests | 3/3 |
| agents-md-change-runs-nothing | 3/3 |
| tests-row-names-its-paths | 3/3 |
| docs-site-row-names-its-paths | 3/3 |
| agents-md-keeps-the-rest | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| no-second-workflow-doc | 3/3 |
