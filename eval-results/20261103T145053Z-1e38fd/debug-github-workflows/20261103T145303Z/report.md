# Eval report: debug-github-workflows

- Timestamp: 20261103T145303Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T145053Z-1e38fd; started 2026-11-03T14:53:03Z, ended 2026-11-03T14:54:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.20, judge $0.14, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.1104 / 0.1104 |
| without_skill | 1 | 0 | 6/7 | error | 0.0846 / 0.0846 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1104 / 0.1104 | 0.0846 / 0.0846 | +0.0258 | +0.0258 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 14746 / 14746 | 71494 / 71494 | -56748 | -56748 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 1105 / 1105 | 1532 / 1532 | -427 | -427 |
| cache_creation_input_tokens | 21819 / 21819 | 13109 / 13109 | +8710 | +8710 |
| cache_read_input_tokens | 120513 / 120513 | 168377 / 168377 | -47864 | -47864 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
