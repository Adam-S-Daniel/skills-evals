# Eval report: debug-github-workflows

- Timestamp: 20261103T193409Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T190747Z-781d93; started 2026-11-03T19:34:09Z, ended 2026-11-03T19:35:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.20, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1178 / 0.1178 |
| without_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.0859 / 0.0859 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1178 / 0.1178 | 0.0859 / 0.0859 | +0.0319 | +0.0319 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 20106 / 20106 | 43010 / 43010 | -22904 | -22904 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1238 / 1238 | 1644 / 1644 | -406 | -406 |
| cache_creation_input_tokens | 22439 / 22439 | 12269 / 12269 | +10170 | +10170 |
| cache_read_input_tokens | 156074 / 156074 | 203487 / 203487 | -47413 | -47413 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
