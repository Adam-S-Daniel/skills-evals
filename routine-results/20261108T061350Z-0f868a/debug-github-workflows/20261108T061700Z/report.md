# Eval report: debug-github-workflows

- Timestamp: 20261108T061700Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T061350Z-0f868a; started 2026-11-08T06:17:00Z, ended 2026-11-08T06:17:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1259 / 0.1259 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0772 / 0.0772 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1259 / 0.1259 | 0.0772 / 0.0772 | +0.0487 | +0.0487 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 22169 / 22169 | 19658 / 19658 | +2511 | +2511 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1479 / 1479 | 1252 / 1252 | +227 | +227 |
| cache_creation_input_tokens | 22918 / 22918 | 11974 / 11974 | +10944 | +10944 |
| cache_read_input_tokens | 194392 / 194392 | 167604 / 167604 | +26788 | +26788 |
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
