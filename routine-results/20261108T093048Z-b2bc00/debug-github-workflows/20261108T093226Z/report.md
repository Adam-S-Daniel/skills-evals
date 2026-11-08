# Eval report: debug-github-workflows

- Timestamp: 20261108T093226Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T093048Z-b2bc00; started 2026-11-08T09:32:26Z, ended 2026-11-08T09:35:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 4 call(s); agent $0.62, judge $0.27, guard $0.00; last agent call $0.29

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.3321 / 0.3321 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.2888 / 0.2888 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3321 / 0.3321 | 0.2888 / 0.2888 | +0.0434 | +0.0434 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 60496 / 60496 | 69459 / 69459 | -8963 | -8963 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 2718 / 2718 | 3746 / 3746 | -1028 | -1028 |
| cache_creation_input_tokens | 26992 / 26992 | 18712 / 18712 | +8280 | +8280 |
| cache_read_input_tokens | 278386 / 278386 | 294553 / 294553 | -16167 | -16167 |
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
