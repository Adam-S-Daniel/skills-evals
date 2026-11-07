# Eval report: debug-github-workflows

- Timestamp: 20261107T053649Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T053520Z-89125e; started 2026-11-07T05:36:49Z, ended 2026-11-07T05:37:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 4 call(s); agent $0.21, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.1230 / 0.1230 |
| without_skill | 1 | 0 | 5/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.0865 / 0.0865 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1230 / 0.1230 | 0.0865 / 0.0865 | +0.0366 | +0.0366 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 16809 / 16809 | 23212 / 23212 | -6403 | -6403 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1275 / 1275 | 1554 / 1554 | -279 | -279 |
| cache_creation_input_tokens | 23586 / 23586 | 12613 / 12613 | +10973 | +10973 |
| cache_read_input_tokens | 158987 / 158987 | 204405 / 204405 | -45418 | -45418 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 0/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
