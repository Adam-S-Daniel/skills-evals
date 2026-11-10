# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261110T054357Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T054230Z-107bf8; started 2026-11-10T05:43:57Z, ended 2026-11-10T05:45:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 6 call(s); agent $0.30, judge $0.14, guard $0.00; last agent call $0.10

## Fixture: release-bump-blocked (n=3)

- Prompt: Release PR #41 is stuck BLOCKED: the required `pin-consistency` check is red after the version bump to 0.1.171. Fix the repository so the release is consistent and the check can pass.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3/3 | 7.8 (7.5 to 8.0, 3 judged) | 0.0992 / 0.2976 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0992 / 0.0990 |
| num_turns | 4 / 4 |
| duration_ms | 12982.7 / 12889 |
| input_tokens | 8 / 8 |
| output_tokens | 991.7 / 993 |
| cache_creation_input_tokens | 10207 / 10097 |
| cache_read_input_tokens | 141538.7 / 141734 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| agents-md-bumped | 3/3 |
| second-manifest-bumped | 3/3 |
| history-kept | 3/3 |
