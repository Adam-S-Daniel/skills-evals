# Eval report: debug-github-workflows

- Timestamp: 20261104T032242Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T032009Z-972d6e; started 2026-11-04T03:22:42Z, ended 2026-11-04T03:23:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.20, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1241 / 0.1241 |
| without_skill | 1 | 0 | 6/7 | error | 0.0781 / 0.0781 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1241 / 0.1241 | 0.0781 / 0.0781 | +0.0460 | +0.0460 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 23812 / 23812 | 17626 / 17626 | +6186 | +6186 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1439 / 1439 | 1284 / 1284 | +155 | +155 |
| cache_creation_input_tokens | 22578 / 22578 | 12112 / 12112 | +10466 | +10466 |
| cache_read_input_tokens | 193882 / 193882 | 167631 / 167631 | +26251 | +26251 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 0/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
