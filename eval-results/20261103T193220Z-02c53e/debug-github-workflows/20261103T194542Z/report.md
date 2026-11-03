# Eval report: debug-github-workflows

- Timestamp: 20261103T194542Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T193220Z-02c53e; started 2026-11-03T19:45:42Z, ended 2026-11-03T19:48:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.69, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.97 over 4 call(s); agent $0.55, judge $0.41, guard $0.00; last agent call $0.26

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.2924 / 0.2924 |
| without_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2619 / 0.2619 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2924 / 0.2924 | 0.2619 / 0.2619 | +0.0305 | +0.0305 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 31235 / 31235 | 73434 / 73434 | -42199 | -42199 |
| input_tokens | 12 / 12 | 18 / 18 | -6 | -6 |
| output_tokens | 2444 / 2444 | 3103 / 3103 | -659 | -659 |
| cache_creation_input_tokens | 25439 / 25439 | 16982 / 16982 | +8457 | +8457 |
| cache_read_input_tokens | 200023 / 200023 | 289150 / 289150 | -89127 | -89127 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
