# Eval report: debug-github-workflows

- Timestamp: 20261103T210714Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T204718Z-b80893; started 2026-11-03T21:07:14Z, ended 2026-11-03T21:08:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 4 call(s); agent $0.23, judge $0.16, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1382 / 0.1382 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0874 / 0.0874 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1382 / 0.1382 | 0.0874 / 0.0874 | +0.0507 | +0.0507 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 19803 / 19803 | 32419 / 32419 | -12616 | -12616 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 1901 / 1901 | 1453 / 1453 | +448 | +448 |
| cache_creation_input_tokens | 24827 / 24827 | 14853 / 14853 | +9974 | +9974 |
| cache_read_input_tokens | 198136 / 198136 | 134515 / 134515 | +63621 | +63621 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
