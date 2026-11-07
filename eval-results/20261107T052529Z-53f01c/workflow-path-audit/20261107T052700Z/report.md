# Eval report: workflow-path-audit

- Timestamp: 20261107T052700Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052529Z-53f01c; started 2026-11-07T05:27:00Z, ended 2026-11-07T05:28:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 4 call(s); agent $0.32, judge $0.11, guard $0.00; last agent call $0.14

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 7.5 (7.5 to 7.5, 1 judged) | 0.1777 / 0.1777 |
| without_skill | 1 | 0 | 6/10 | 4.9 (4.9 to 4.9, 1 judged) | 0.1446 / 0.1446 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1777 / 0.1777 | 0.1446 / 0.1446 | +0.0331 | +0.0331 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 34780 / 34780 | 26335 / 26335 | +8445 | +8445 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3271 / 3271 | 2990 / 2990 | +281 | +281 |
| cache_creation_input_tokens | 30754 / 30754 | 24658 / 24658 | +6096 | +6096 |
| cache_read_input_tokens | 219403 / 219403 | 160041 / 160041 | +59362 | +59362 |
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
