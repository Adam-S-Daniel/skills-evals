# Eval report: workflow-path-audit

- Timestamp: 20261107T111612Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T111428Z-d4c517; started 2026-11-07T11:16:12Z, ended 2026-11-07T11:18:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.42, from 9 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.79 over 8 call(s); agent $0.58, judge $0.20, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=2)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 6/10 | 5.0 (4.5 to 5.5, 2 judged) | 0.1439 / 0.2878 |
| without_skill | 2 | 0 | 8/10 | 7.3 (5.5 to 9.1, 2 judged) | 0.1477 / 0.2953 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1439 / 0.1439 | 0.1477 / 0.1477 | -0.0038 | -0.0038 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 24325 / 24325 | 28867.5 / 28867.5 | -4542.5 | -4542.5 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2798.5 / 2798.5 | 2797.5 / 2797.5 | +1 | +1 |
| cache_creation_input_tokens | 24947.5 / 24947.5 | 24956 / 24956 | -8.5 | -8.5 |
| cache_read_input_tokens | 160925.5 / 160925.5 | 198471.5 / 198471.5 | -37546 | -37546 |
| tool_errors | 0 / 0 | 0.5 / 0.5 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/2 | 1/2 |
| source-change-runs-only-the-tests | 0/2 | 1/2 |
| lockfile-change-runs-only-the-tests | 0/2 | 1/2 |
| agents-md-change-runs-nothing | 0/2 | 1/2 |
| tests-row-names-its-paths | 2/2 | 2/2 |
| docs-site-row-names-its-paths | 2/2 | 2/2 |
| agents-md-keeps-the-rest | 2/2 | 2/2 |
| workflows-still-parse | 2/2 | 2/2 |
| event-only-workflows-unfiltered | 2/2 | 2/2 |
| no-second-workflow-doc | 2/2 | 2/2 |
