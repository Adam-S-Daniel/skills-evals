# Eval report: debug-github-workflows

- Timestamp: 20261108T071125Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T070121Z-0c03dd; started 2026-11-08T07:11:25Z, ended 2026-11-08T07:13:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 4 call(s); agent $0.55, judge $0.28, guard $0.00; last agent call $0.21

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.3352 / 0.3352 |
| without_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.2101 / 0.2101 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3352 / 0.3352 | 0.2101 / 0.2101 | +0.1251 | +0.1251 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 57919 / 57919 | 30133 / 30133 | +27786 | +27786 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 3027 / 3027 | 2320 / 2320 | +707 | +707 |
| cache_creation_input_tokens | 27467 / 27467 | 14293 / 14293 | +13174 | +13174 |
| cache_read_input_tokens | 241584 / 241584 | 246439 / 246439 | -4855 | -4855 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 1/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 0/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
