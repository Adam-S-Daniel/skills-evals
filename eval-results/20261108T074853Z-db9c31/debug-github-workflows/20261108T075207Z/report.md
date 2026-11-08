# Eval report: debug-github-workflows

- Timestamp: 20261108T075207Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T074853Z-db9c31; started 2026-11-08T07:52:07Z, ended 2026-11-08T07:53:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1432 / 0.1432 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0875 / 0.0875 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1432 / 0.1432 | 0.0875 / 0.0875 | +0.0558 | +0.0558 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 33882 / 33882 | 25577 / 25577 | +8305 | +8305 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 1779 / 1779 | 1510 / 1510 | +269 | +269 |
| cache_creation_input_tokens | 24519 / 24519 | 12944 / 12944 | +11575 | +11575 |
| cache_read_input_tokens | 273443 / 273443 | 205879 / 205879 | +67564 | +67564 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 0/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
