# Eval report: debug-github-workflows

- Timestamp: 20261108T131224Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T131045Z-c9535b; started 2026-11-08T13:12:24Z, ended 2026-11-08T13:14:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 4 call(s); agent $0.50, judge $0.19, guard $0.00; last agent call $0.20

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2912 / 0.2912 |
| without_skill | 1 | 0 | 6/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.2042 / 0.2042 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2912 / 0.2912 | 0.2042 / 0.2042 | +0.0870 | +0.0870 |
| num_turns | 5 / 5 | 7 / 7 | -2 | -2 |
| duration_ms | 37793 / 37793 | 35319 / 35319 | +2474 | +2474 |
| input_tokens | 10 / 10 | 14 / 14 | -4 | -4 |
| output_tokens | 2592 / 2592 | 2294 / 2294 | +298 | +298 |
| cache_creation_input_tokens | 25883 / 25883 | 13675 / 13675 | +12208 | +12208 |
| cache_read_input_tokens | 161419 / 161419 | 244373 / 244373 | -82954 | -82954 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 0/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
