# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T213856Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T213705Z-dab361; started 2026-11-07T21:38:56Z, ended 2026-11-07T21:39:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.26, judge $0.07, guard $0.00; last agent call $0.13

## Fixture: release-bump-blocked (n=1)

- Prompt: Release PR #41 is stuck BLOCKED: the required `pin-consistency` check is red after the version bump to 0.1.171. Fix the repository so the release is consistent and the check can pass.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.1303 / 0.1303 |
| without_skill | 1 | 0 | 3/3 | 8.0 (8.0 to 8.0, 1 judged) | 0.1268 / 0.1268 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1303 / 0.1303 | 0.1268 / 0.1268 | +0.0035 | +0.0035 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 18307 / 18307 | 13664 / 13664 | +4643 | +4643 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1092 / 1092 | 939 / 939 | +153 | +153 |
| cache_creation_input_tokens | 25582 / 25582 | 25116 / 25116 | +466 | +466 |
| cache_read_input_tokens | 170151 / 170151 | 168808 / 168808 | +1343 | +1343 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| agents-md-bumped | 1/1 | 1/1 |
| second-manifest-bumped | 1/1 | 1/1 |
| history-kept | 1/1 | 1/1 |
