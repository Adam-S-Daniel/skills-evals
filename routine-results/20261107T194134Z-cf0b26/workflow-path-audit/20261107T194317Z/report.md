# Eval report: workflow-path-audit

- Timestamp: 20261107T194317Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194134Z-cf0b26; started 2026-11-07T19:43:17Z, ended 2026-11-07T19:51:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.21 over 12 call(s); agent $2.46, judge $0.75, guard $0.00; last agent call $0.42

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 9.0 (8.9 to 9.1, 3 judged) | 0.4204 / 1.2611 |
| without_skill | 3 | 0 | 10/10 | 9.0 (8.9 to 9.1, 3 judged) | 0.4005 / 1.2016 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4204 / 0.4223 | 0.4005 / 0.3977 | +0.0198 | +0.0247 |
| num_turns | 9.3 / 9 | 7.7 / 8 | +1.7 | +1 |
| duration_ms | 63294.3 / 60196 | 70890.3 / 69305 | -7596 | -9109 |
| input_tokens | 18 / 18 | 17.3 / 18 | +0.7 | 0 |
| output_tokens | 4094.3 / 3953 | 4197.7 / 4274 | -103.3 | -321 |
| cache_creation_input_tokens | 34523.3 / 35089 | 31666.3 / 31418 | +2857 | +3671 |
| cache_read_input_tokens | 291399.7 / 280236 | 286436 / 296579 | +4963.7 | -16343 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

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
