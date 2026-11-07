# Eval report: workflow-path-audit

- Timestamp: 20261107T072032Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T071901Z-bd369f; started 2026-11-07T07:20:32Z, ended 2026-11-07T07:21:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 4 call(s); agent $0.31, judge $0.11, guard $0.00; last agent call $0.14

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 5.5 (5.5 to 5.5, 1 judged) | 0.1659 / 0.1659 |
| without_skill | 1 | 0 | 6/10 | 4.6 (4.6 to 4.6, 1 judged) | 0.1398 / 0.1398 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1659 / 0.1659 | 0.1398 / 0.1398 | +0.0261 | +0.0261 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 34395 / 34395 | 26211 / 26211 | +8184 | +8184 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 3478 / 3478 | 2878 / 2878 | +600 | +600 |
| cache_creation_input_tokens | 26685 / 26685 | 24712 / 24712 | +1973 | +1973 |
| cache_read_input_tokens | 243321 / 243321 | 121657 / 121657 | +121664 | +121664 |
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
| no-second-workflow-doc | 1/1 | 1/1 |
