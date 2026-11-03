# Eval report: debug-github-workflows

- Timestamp: 20261103T041232Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T041055Z-42a60d; started 2026-11-03T04:12:32Z, ended 2026-11-03T04:13:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.20, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1207 / 0.1207 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0815 / 0.0815 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1207 / 0.1207 | 0.0815 / 0.0815 | +0.0392 | +0.0392 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 18294 / 18294 | 16391 / 16391 | +1903 | +1903 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1383 / 1383 | 1236 / 1236 | +147 | +147 |
| cache_creation_input_tokens | 22772 / 22772 | 13042 / 13042 | +9730 | +9730 |
| cache_read_input_tokens | 157658 / 157658 | 169565 / 169565 | -11907 | -11907 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
