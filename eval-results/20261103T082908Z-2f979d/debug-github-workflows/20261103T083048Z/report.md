# Eval report: debug-github-workflows

- Timestamp: 20261103T083048Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T082908Z-2f979d; started 2026-11-03T08:30:48Z, ended 2026-11-03T08:34:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.44 over 4 call(s); agent $0.92, judge $0.52, guard $0.00; last agent call $0.41

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.5095 / 0.5095 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.4099 / 0.4099 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5095 / 0.5095 | 0.4099 / 0.4099 | +0.0996 | +0.0996 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 82309 / 82309 | 110107 / 110107 | -27798 | -27798 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3984 / 3984 | 4725 / 4725 | -741 | -741 |
| cache_creation_input_tokens | 29824 / 29824 | 20430 / 20430 | +9394 | +9394 |
| cache_read_input_tokens | 206088 / 206088 | 214284 / 214284 | -8196 | -8196 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
