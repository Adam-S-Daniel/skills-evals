# Eval report: debug-github-workflows

- Timestamp: 20261107T043732Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T043607Z-74ba22; started 2026-11-07T04:37:32Z, ended 2026-11-07T04:39:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.21, judge $0.09, guard $0.00; last agent call $0.09

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 6.8 (6.8 to 6.8, 1 judged) | 0.1267 / 0.1267 |
| without_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0875 / 0.0875 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1267 / 0.1267 | 0.0875 / 0.0875 | +0.0393 | +0.0393 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 18110 / 18110 | 54401 / 54401 | -36291 | -36291 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1354 / 1354 | 1675 / 1675 | -321 | -321 |
| cache_creation_input_tokens | 24279 / 24279 | 12558 / 12558 | +11721 | +11721 |
| cache_read_input_tokens | 160542 / 160542 | 204523 / 204523 | -43981 | -43981 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
