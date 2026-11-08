# Eval report: debug-github-workflows

- Timestamp: 20261108T084754Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T084303Z-890cf5; started 2026-11-08T08:47:54Z, ended 2026-11-08T08:48:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.20, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.1134 / 0.1134 |
| without_skill | 1 | 0 | 5/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.0844 / 0.0844 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1134 / 0.1134 | 0.0844 / 0.0844 | +0.0290 | +0.0290 |
| num_turns | 4 / 4 | 7 / 7 | -3 | -3 |
| duration_ms | 15798 / 15798 | 23490 / 23490 | -7692 | -7692 |
| input_tokens | 8 / 8 | 12 / 12 | -4 | -4 |
| output_tokens | 1151 / 1151 | 1479 / 1479 | -328 | -328 |
| cache_creation_input_tokens | 22458 / 22458 | 12286 / 12286 | +10172 | +10172 |
| cache_read_input_tokens | 120619 / 120619 | 204282 / 204282 | -83663 | -83663 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 0/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
