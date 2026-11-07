# Eval report: workflow-path-audit

- Timestamp: 20261107T152731Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152544Z-4f4654; started 2026-11-07T15:27:31Z, ended 2026-11-07T15:35:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.5, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.13 over 12 call(s); agent $2.40, judge $0.73, guard $0.00; last agent call $0.39

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 8.9 (8.8 to 9.1, 3 judged) | 0.4228 / 1.2684 |
| without_skill | 3 | 0 | 10/10 | 9.3 (8.8 to 10.0, 3 judged) | 0.3784 / 1.1352 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4228 / 0.4165 | 0.3784 / 0.3832 | +0.0444 | +0.0332 |
| num_turns | 8.7 / 8 | 6.7 / 7 | +2 | +1 |
| duration_ms | 72334.7 / 64136 | 64688 / 63775 | +7646.7 | +361 |
| input_tokens | 17.3 / 16 | 15.3 / 16 | +2 | 0 |
| output_tokens | 3852.7 / 3781 | 3939 / 4070 | -86.3 | -289 |
| cache_creation_input_tokens | 35778 / 36072 | 30626.7 / 30538 | +5151.3 | +5534 |
| cache_read_input_tokens | 265252.3 / 236048 | 241261.7 / 256295 | +23990.7 | -20247 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 3/3 | 3/3 |
| source-change-runs-only-the-tests | 3/3 | 3/3 |
| lockfile-change-runs-only-the-tests | 3/3 | 3/3 |
| agents-md-change-runs-nothing | 3/3 | 3/3 |
| tests-row-names-its-paths | 3/3 | 3/3 |
| docs-site-row-names-its-paths | 3/3 | 3/3 |
| agents-md-keeps-the-rest | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| no-second-workflow-doc | 3/3 | 3/3 |
