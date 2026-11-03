# Eval report: debug-github-workflows

- Timestamp: 20261103T202609Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T200922Z-acb1e8; started 2026-11-03T20:26:09Z, ended 2026-11-03T20:27:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.7, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.21, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.1330 / 0.1330 |
| without_skill | 1 | 0 | 5/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.0751 / 0.0751 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1330 / 0.1330 | 0.0751 / 0.0751 | +0.0578 | +0.0578 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 34338 / 34338 | 18667 / 18667 | +15671 | +15671 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 1635 / 1635 | 1143 / 1143 | +492 | +492 |
| cache_creation_input_tokens | 23374 / 23374 | 11755 / 11755 | +11619 | +11619 |
| cache_read_input_tokens | 231007 / 231007 | 166755 / 166755 | +64252 | +64252 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 0/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
