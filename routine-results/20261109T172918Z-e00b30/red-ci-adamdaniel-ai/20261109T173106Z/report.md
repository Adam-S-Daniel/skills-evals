# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261109T173106Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T172918Z-e00b30; started 2026-11-09T17:31:06Z, ended 2026-11-09T17:32:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.02, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.20, judge $0.08, guard $0.00; last agent call $0.04

## Fixture: release-bump-blocked (n=3)

- Prompt: Release PR #41 is stuck BLOCKED: the required `pin-consistency` check is red after the version bump to 0.1.171. Fix the repository so the release is consistent and the check can pass.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3/3 | 8.0 (7.3 to 8.3, 3 judged) | 0.0683 / 0.2048 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0683 / 0.0454 |
| num_turns | 4 / 4 |
| duration_ms | 10774.3 / 9906 |
| input_tokens | 8 / 8 |
| output_tokens | 783.3 / 777 |
| cache_creation_input_tokens | 18912.7 / 9276 |
| cache_read_input_tokens | 131230.3 / 140836 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| agents-md-bumped | 3/3 |
| second-manifest-bumped | 3/3 |
| history-kept | 3/3 |
