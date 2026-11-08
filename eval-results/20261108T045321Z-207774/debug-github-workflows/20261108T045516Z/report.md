# Eval report: debug-github-workflows

- Timestamp: 20261108T045516Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T045321Z-207774; started 2026-11-08T04:55:16Z, ended 2026-11-08T04:57:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 2 call(s); agent $0.60, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3696 / 0.3696 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2285 / 0.2285 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3696 / 0.3696 | 0.2285 / 0.2285 | +0.1412 | +0.1412 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 71755 / 71755 | 49290 / 49290 | +22465 | +22465 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 3347 / 3347 | 2577 / 2577 | +770 | +770 |
| cache_creation_input_tokens | 28970 / 28970 | 15431 / 15431 | +13539 | +13539 |
| cache_read_input_tokens | 324938 / 324938 | 246244 / 246244 | +78694 | +78694 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 1/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
