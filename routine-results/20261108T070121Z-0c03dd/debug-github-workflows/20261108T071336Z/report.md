# Eval report: debug-github-workflows

- Timestamp: 20261108T071336Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T070121Z-0c03dd; started 2026-11-08T07:13:36Z, ended 2026-11-08T07:14:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1197 / 0.1197 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0767 / 0.0767 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1197 / 0.1197 | 0.0767 / 0.0767 | +0.0430 | +0.0430 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 18145 / 18145 | 20502 / 20502 | -2357 | -2357 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1217 / 1217 | 1335 / 1335 | -118 | -118 |
| cache_creation_input_tokens | 22942 / 22942 | 11667 / 11667 | +11275 | +11275 |
| cache_read_input_tokens | 157271 / 157271 | 166693 / 166693 | -9422 | -9422 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 0/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
