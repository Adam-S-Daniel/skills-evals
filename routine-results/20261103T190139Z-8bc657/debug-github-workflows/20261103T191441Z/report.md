# Eval report: debug-github-workflows

- Timestamp: 20261103T191441Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T190139Z-8bc657; started 2026-11-03T19:14:41Z, ended 2026-11-03T19:18:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.33 over 4 call(s); agent $0.85, judge $0.47, guard $0.00; last agent call $0.38

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4737 / 0.4737 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.3793 / 0.3793 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4737 / 0.4737 | 0.3793 / 0.3793 | +0.0944 | +0.0944 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 90789 / 90789 | 70257 / 70257 | +20532 | +20532 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4078 / 4078 | 3980 / 3980 | +98 | +98 |
| cache_creation_input_tokens | 30410 / 30410 | 19672 / 19672 | +10738 | +10738 |
| cache_read_input_tokens | 204131 / 204131 | 213886 / 213886 | -9755 | -9755 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
