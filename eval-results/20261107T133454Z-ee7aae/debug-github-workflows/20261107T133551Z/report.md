# Eval report: debug-github-workflows

- Timestamp: 20261107T133551Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T133454Z-ee7aae; started 2026-11-07T13:35:51Z, ended 2026-11-07T13:38:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.94 over 6 call(s); agent $0.59, judge $0.35, guard $0.00; last agent call $0.19

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.7/7 | 8.9 (8.8 to 9.0, 3 judged) | 0.1971 / 0.5912 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1971 / 0.1888 |
| num_turns | 7.7 / 8 |
| duration_ms | 39375.7 / 35240 |
| input_tokens | 14.7 / 14 |
| output_tokens | 2113.7 / 2077 |
| cache_creation_input_tokens | 12539.3 / 11937 |
| cache_read_input_tokens | 272083.7 / 258544 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| failure-evidence-read-without-writes | 3/3 |
| suite-passes-without-a-git-identity | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 |
| reply-reads-the-exit-code | 3/3 |
| reply-names-the-git-identity | 2/3 |
| sources-tests-and-workflow-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
