# Eval report: workflow-path-audit

- Timestamp: 20261107T204422Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T204250Z-455b93; started 2026-11-07T20:44:22Z, ended 2026-11-07T20:48:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.38 over 4 call(s); agent $1.04, judge $0.34, guard $0.00; last agent call $0.37

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/10 | error | 0.6699 / 0.6699 |
| without_skill | 1 | 0 | 10/10 | 9.0 (9.0 to 9.0, 1 judged) | 0.3718 / 0.3718 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6699 / 0.6699 | 0.3718 / 0.3718 | +0.2980 | +0.2980 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 126136 / 126136 | 44326 / 44326 | +81810 | +81810 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 7394 / 7394 | 4174 / 4174 | +3220 | +3220 |
| cache_creation_input_tokens | 39123 / 39123 | 29739 / 29739 | +9384 | +9384 |
| cache_read_input_tokens | 328681 / 328681 | 251985 / 251985 | +76696 | +76696 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 1/1 |
| source-change-runs-only-the-tests | 0/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 1/1 |
| agents-md-change-runs-nothing | 0/1 | 1/1 |
| tests-row-names-its-paths | 0/1 | 1/1 |
| docs-site-row-names-its-paths | 0/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
