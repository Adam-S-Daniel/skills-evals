# Eval report: workflow-path-audit

- Timestamp: 20261107T130005Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T125910Z-f2348c; started 2026-11-07T13:00:05Z, ended 2026-11-07T13:01:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 6 call(s); agent $0.24, judge $0.10, guard $0.00; last agent call $0.09

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 8.7/10 | 6.1 (4.1 to 10.0, 3 judged) | 0.0796 / 0.2389 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0796 / 0.0773 |
| num_turns | 5.3 / 5 |
| duration_ms | 23472.7 / 19217 |
| input_tokens | 10.7 / 10 |
| output_tokens | 1329 / 1201 |
| cache_creation_input_tokens | 11758 / 11818 |
| cache_read_input_tokens | 192966.7 / 179823 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| docs-change-builds-only-the-docs | 3/3 |
| source-change-runs-only-the-tests | 3/3 |
| lockfile-change-runs-only-the-tests | 3/3 |
| agents-md-change-runs-nothing | 3/3 |
| tests-row-names-its-paths | 1/3 |
| docs-site-row-names-its-paths | 1/3 |
| agents-md-keeps-the-rest | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| no-second-workflow-doc | 3/3 |
