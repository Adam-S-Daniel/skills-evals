# Eval report: workflow-path-audit

- Timestamp: 20261107T153554Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152544Z-4f4654; started 2026-11-07T15:35:54Z, ended 2026-11-07T15:39:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 6 call(s); agent $0.89, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.3/10 | skipped (objective-decided) | 0.1386 / 0.4159 |
| without_skill | 3 | 0 | 5.7/10 | skipped (objective-decided) | 0.1573 / 0.4719 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1386 / 0.1436 | 0.1573 / 0.1498 | -0.0187 | -0.0062 |
| num_turns | 5 / 5 | 5.7 / 5 | -0.7 | 0 |
| duration_ms | 30190.7 / 30878 | 34270 / 31893 | -4079.3 | -1015 |
| input_tokens | 10 / 10 | 11.3 / 10 | -1.3 | 0 |
| output_tokens | 2488.3 / 2783 | 3582 / 3135 | -1093.7 | -352 |
| cache_creation_input_tokens | 24444 / 24594 | 25666 / 25595 | -1222 | -1001 |
| cache_read_input_tokens | 159448.3 / 159174 | 187851 / 160111 | -28402.7 | -937 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 1/3 | 0/3 |
| source-change-runs-only-the-tests | 1/3 | 0/3 |
| lockfile-change-runs-only-the-tests | 1/3 | 0/3 |
| agents-md-change-runs-nothing | 1/3 | 0/3 |
| tests-row-names-its-paths | 3/3 | 3/3 |
| docs-site-row-names-its-paths | 3/3 | 3/3 |
| agents-md-keeps-the-rest | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| no-second-workflow-doc | 3/3 | 2/3 |
