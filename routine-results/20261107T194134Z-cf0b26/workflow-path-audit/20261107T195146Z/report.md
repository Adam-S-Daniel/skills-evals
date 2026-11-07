# Eval report: workflow-path-audit

- Timestamp: 20261107T195146Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194134Z-cf0b26; started 2026-11-07T19:51:46Z, ended 2026-11-07T19:55:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.66, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.07 over 12 call(s); agent $0.83, judge $0.24, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=3)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.7/10 | 8.8 (6.5 to 10.0, 3 judged) | 0.1320 / 0.3960 |
| without_skill | 3 | 0 | 8.7/10 | 8.5 (7.0 to 9.4, 3 judged) | 0.1460 / 0.4379 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1320 / 0.1234 | 0.1460 / 0.1510 | -0.0140 | -0.0276 |
| num_turns | 4.3 / 4 | 6.7 / 6 | -2.3 | -2 |
| duration_ms | 21292.7 / 17742 | 29086.7 / 31579 | -7794 | -13837 |
| input_tokens | 8.7 / 8 | 13.3 / 12 | -4.7 | -4 |
| output_tokens | 2088 / 1517 | 2434.3 / 2309 | -346.3 | -792 |
| cache_creation_input_tokens | 24390.7 / 24034 | 24803.3 / 25093 | -412.7 | -1059 |
| cache_read_input_tokens | 135280.7 / 122711 | 223935.3 / 200603 | -88654.7 | -77892 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 2/3 | 2/3 |
| source-change-runs-only-the-tests | 2/3 | 2/3 |
| lockfile-change-runs-only-the-tests | 2/3 | 2/3 |
| agents-md-change-runs-nothing | 2/3 | 2/3 |
| tests-row-names-its-paths | 3/3 | 3/3 |
| docs-site-row-names-its-paths | 3/3 | 3/3 |
| agents-md-keeps-the-rest | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| no-second-workflow-doc | 3/3 | 3/3 |
