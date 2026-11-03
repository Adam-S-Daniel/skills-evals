# Eval report: debug-github-workflows

- Timestamp: 20261103T205013Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T203334Z-11d954; started 2026-11-03T20:50:13Z, ended 2026-11-03T20:53:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.71, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.45 over 4 call(s); agent $0.94, judge $0.51, guard $0.00; last agent call $0.43

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.5070 / 0.5070 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.4329 / 0.4329 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5070 / 0.5070 | 0.4329 / 0.4329 | +0.0740 | +0.0740 |
| num_turns | 6 / 6 | 8 / 8 | -2 | -2 |
| duration_ms | 73940 / 73940 | 79096 / 79096 | -5156 | -5156 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 4191 / 4191 | 4180 / 4180 | +11 | +11 |
| cache_creation_input_tokens | 29866 / 29866 | 22352 / 22352 | +7514 | +7514 |
| cache_read_input_tokens | 205307 / 205307 | 298908 / 298908 | -93601 | -93601 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
