# Eval report: debug-github-workflows

- Timestamp: 20261103T151346Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T151146Z-7cdf63; started 2026-11-03T15:13:46Z, ended 2026-11-03T15:14:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1222 / 0.1222 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.0942 / 0.0942 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1222 / 0.1222 | 0.0942 / 0.0942 | +0.0281 | +0.0281 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 19751 / 19751 | 24745 / 24745 | -4994 | -4994 |
| input_tokens | 8 / 8 | 12 / 12 | -4 | -4 |
| output_tokens | 1666 / 1666 | 1670 / 1670 | -4 | -4 |
| cache_creation_input_tokens | 23366 / 23366 | 14232 / 14232 | +9134 | +9134 |
| cache_read_input_tokens | 120981 / 120981 | 205037 / 205037 | -84056 | -84056 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
