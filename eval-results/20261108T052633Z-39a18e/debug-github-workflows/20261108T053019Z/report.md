# Eval report: debug-github-workflows

- Timestamp: 20261108T053019Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T052633Z-39a18e; started 2026-11-08T05:30:19Z, ended 2026-11-08T05:31:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.20, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1219 / 0.1219 |
| without_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.0802 / 0.0802 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1219 / 0.1219 | 0.0802 / 0.0802 | +0.0416 | +0.0416 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 20946 / 20946 | 17704 / 17704 | +3242 | +3242 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1332 / 1332 | 1364 / 1364 | -32 | -32 |
| cache_creation_input_tokens | 22320 / 22320 | 12460 / 12460 | +9860 | +9860 |
| cache_read_input_tokens | 192697 / 192697 | 167460 / 167460 | +25237 | +25237 |
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
