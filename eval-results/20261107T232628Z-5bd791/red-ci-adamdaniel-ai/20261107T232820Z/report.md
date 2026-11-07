# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T232820Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T232628Z-5bd791; started 2026-11-07T23:28:20Z, ended 2026-11-07T23:29:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.25, judge $0.06, guard $0.00; last agent call $0.13

## Fixture: release-bump-blocked (n=1)

- Prompt: Release PR #41 is stuck BLOCKED: the required `pin-consistency` check is red after the version bump to 0.1.171. Fix the repository so the release is consistent and the check can pass.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.1213 / 0.1213 |
| without_skill | 1 | 0 | 3/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.1263 / 0.1263 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1213 / 0.1213 | 0.1263 / 0.1263 | -0.0050 | -0.0050 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 10192 / 10192 | 12385 / 12385 | -2193 | -2193 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 803 / 803 | 978 / 978 | -175 | -175 |
| cache_creation_input_tokens | 25075 / 25075 | 24923 / 24923 | +152 | +152 |
| cache_read_input_tokens | 130014 / 130014 | 168271 / 168271 | -38257 | -38257 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| agents-md-bumped | 1/1 | 1/1 |
| second-manifest-bumped | 1/1 | 1/1 |
| history-kept | 1/1 | 1/1 |
