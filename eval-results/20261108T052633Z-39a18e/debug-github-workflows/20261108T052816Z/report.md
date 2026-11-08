# Eval report: debug-github-workflows

- Timestamp: 20261108T052816Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T052633Z-39a18e; started 2026-11-08T05:28:16Z, ended 2026-11-08T05:30:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 4 call(s); agent $0.57, judge $0.24, guard $0.00; last agent call $0.22

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.3439 / 0.3439 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2222 / 0.2222 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3439 / 0.3439 | 0.2222 / 0.2222 | +0.1217 | +0.1217 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 46657 / 46657 | 34178 / 34178 | +12479 | +12479 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 3139 / 3139 | 2449 / 2449 | +690 | +690 |
| cache_creation_input_tokens | 27462 / 27462 | 14507 / 14507 | +12955 | +12955 |
| cache_read_input_tokens | 280100 / 280100 | 285323 / 285323 | -5223 | -5223 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 1/1 | 1/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
