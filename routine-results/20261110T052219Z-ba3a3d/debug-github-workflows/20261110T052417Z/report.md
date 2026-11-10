# Eval report: debug-github-workflows

- Timestamp: 20261110T052417Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T052219Z-ba3a3d; started 2026-11-10T05:24:17Z, ended 2026-11-10T05:27:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.08 over 4 call(s); agent $0.86, judge $0.21, guard $0.00; last agent call $0.36

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.5018 / 0.5018 |
| without_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.3619 / 0.3619 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5018 / 0.5018 | 0.3619 / 0.3619 | +0.1399 | +0.1399 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 79530 / 79530 | 90573 / 90573 | -11043 | -11043 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4709 / 4709 | 4341 / 4341 | +368 | +368 |
| cache_creation_input_tokens | 46251 / 46251 | 20881 / 20881 | +25370 | +25370 |
| cache_read_input_tokens | 193128 / 193128 | 217501 / 217501 | -24373 | -24373 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
