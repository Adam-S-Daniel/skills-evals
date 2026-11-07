# Eval report: debug-github-workflows

- Timestamp: 20261107T085310Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T085214Z-d1472c; started 2026-11-07T08:53:10Z, ended 2026-11-07T08:54:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 6 call(s); agent $0.31, judge $0.11, guard $0.00; last agent call $0.06

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.3/7 | 8.2 (7.4 to 9.0, 3 judged) | 0.1033 / 0.3099 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1033 / 0.0779 |
| num_turns | 4.7 / 4 |
| duration_ms | 22588 / 16585 |
| input_tokens | 9.3 / 8 |
| output_tokens | 1112.3 / 979 |
| cache_creation_input_tokens | 19159.7 / 10490 |
| cache_read_input_tokens | 155310.3 / 139431 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| failure-evidence-read-without-writes | 0/3 |
| suite-passes-without-a-git-identity | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 |
| reply-reads-the-exit-code | 1/3 |
| reply-names-the-git-identity | 3/3 |
| sources-tests-and-workflow-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
