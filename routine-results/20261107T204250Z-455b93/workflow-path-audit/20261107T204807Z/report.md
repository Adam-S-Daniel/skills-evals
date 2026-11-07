# Eval report: workflow-path-audit

- Timestamp: 20261107T204807Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T204250Z-455b93; started 2026-11-07T20:48:07Z, ended 2026-11-07T20:49:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.31, judge $0.09, guard $0.00; last agent call $0.13

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.3 (6.3 to 6.3, 1 judged) | 0.1789 / 0.1789 |
| without_skill | 1 | 0 | 10/10 | 10.0 (10.0 to 10.0, 1 judged) | 0.1290 / 0.1290 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1789 / 0.1789 | 0.1290 / 0.1290 | +0.0499 | +0.0499 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 29545 / 29545 | 20223 / 20223 | +9322 | +9322 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3215 / 3215 | 1580 / 1580 | +1635 | +1635 |
| cache_creation_input_tokens | 31191 / 31191 | 24278 / 24278 | +6913 | +6913 |
| cache_read_input_tokens | 219278 / 219278 | 160464 / 160464 | +58814 | +58814 |
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
