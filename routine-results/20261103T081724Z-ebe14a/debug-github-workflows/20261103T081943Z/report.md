# Eval report: debug-github-workflows

- Timestamp: 20261103T081943Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T081724Z-ebe14a; started 2026-11-03T08:19:43Z, ended 2026-11-03T08:22:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 4 call(s); agent $0.57, judge $0.44, guard $0.00; last agent call $0.28

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.2897 / 0.2897 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2779 / 0.2779 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2897 / 0.2897 | 0.2779 / 0.2779 | +0.0118 | +0.0118 |
| num_turns | 6 / 6 | 9 / 9 | -3 | -3 |
| duration_ms | 33981 / 33981 | 61351 / 61351 | -27370 | -27370 |
| input_tokens | 12 / 12 | 18 / 18 | -6 | -6 |
| output_tokens | 2174 / 2174 | 3204 / 3204 | -1030 | -1030 |
| cache_creation_input_tokens | 25752 / 25752 | 18619 / 18619 | +7133 | +7133 |
| cache_read_input_tokens | 200815 / 200815 | 295475 / 295475 | -94660 | -94660 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 1/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 0/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
