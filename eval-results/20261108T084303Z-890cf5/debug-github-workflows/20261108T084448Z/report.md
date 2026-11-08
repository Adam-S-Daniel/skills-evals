# Eval report: debug-github-workflows

- Timestamp: 20261108T084448Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T084303Z-890cf5; started 2026-11-08T08:44:48Z, ended 2026-11-08T08:47:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 4 call(s); agent $0.66, judge $0.34, guard $0.00; last agent call $0.30

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.3636 / 0.3636 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2973 / 0.2973 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3636 / 0.3636 | 0.2973 / 0.2973 | +0.0663 | +0.0663 |
| num_turns | 9 / 9 | 9 / 9 | 0 | 0 |
| duration_ms | 52538 / 52538 | 74350 / 74350 | -21812 | -21812 |
| input_tokens | 20 / 20 | 20 / 20 | 0 | 0 |
| output_tokens | 3606 / 3606 | 4352 / 4352 | -746 | -746 |
| cache_creation_input_tokens | 27838 / 27838 | 17544 / 17544 | +10294 | +10294 |
| cache_read_input_tokens | 316270 / 316270 | 326776 / 326776 | -10506 | -10506 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 1/1 | 1/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
