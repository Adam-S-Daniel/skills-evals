# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261108T014411Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T014228Z-2c064d; started 2026-11-08T01:44:11Z, ended 2026-11-08T01:44:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.25, judge $0.06, guard $0.00; last agent call $0.12

## Fixture: release-bump-blocked (n=1)

- Prompt: Release PR #41 is stuck BLOCKED: the required `pin-consistency` check is red after the version bump to 0.1.171. Fix the repository so the release is consistent and the check can pass.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/3 | 8.5 (8.5 to 8.5, 1 judged) | 0.1305 / 0.1305 |
| without_skill | 1 | 0 | 3/3 | 8.0 (8.0 to 8.0, 1 judged) | 0.1219 / 0.1219 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1305 / 0.1305 | 0.1219 / 0.1219 | +0.0086 | +0.0086 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 15316 / 15316 | 10228 / 10228 | +5088 | +5088 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1147 / 1147 | 848 / 848 | +299 | +299 |
| cache_creation_input_tokens | 25499 / 25499 | 25111 / 25111 | +388 | +388 |
| cache_read_input_tokens | 169705 / 169705 | 129639 / 129639 | +40066 | +40066 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| agents-md-bumped | 1/1 | 1/1 |
| second-manifest-bumped | 1/1 | 1/1 |
| history-kept | 1/1 | 1/1 |
