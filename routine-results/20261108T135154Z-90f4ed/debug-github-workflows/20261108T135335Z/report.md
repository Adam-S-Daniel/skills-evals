# Eval report: debug-github-workflows

- Timestamp: 20261108T135335Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T135154Z-90f4ed; started 2026-11-08T13:53:35Z, ended 2026-11-08T13:56:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.77, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 4 call(s); agent $0.59, judge $0.23, guard $0.00; last agent call $0.26

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.3315 / 0.3315 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2632 / 0.2632 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3315 / 0.3315 | 0.2632 / 0.2632 | +0.0683 | +0.0683 |
| num_turns | 10 / 10 | 8 / 8 | +2 | +2 |
| duration_ms | 37261 / 37261 | 74136 / 74136 | -36875 | -36875 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 2707 / 2707 | 3314 / 3314 | -607 | -607 |
| cache_creation_input_tokens | 27588 / 27588 | 16690 / 16690 | +10898 | +10898 |
| cache_read_input_tokens | 282753 / 282753 | 289073 / 289073 | -6320 | -6320 |
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
