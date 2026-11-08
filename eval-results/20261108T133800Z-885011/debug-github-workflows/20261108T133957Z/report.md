# Eval report: debug-github-workflows

- Timestamp: 20261108T133957Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T133800Z-885011; started 2026-11-08T13:39:57Z, ended 2026-11-08T13:43:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.77, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.24 over 4 call(s); agent $0.92, judge $0.32, guard $0.00; last agent call $0.42

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.5039 / 0.5039 |
| without_skill | 1 | 0 | 6/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4197 / 0.4197 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5039 / 0.5039 | 0.4197 / 0.4197 | +0.0842 | +0.0842 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 79730 / 79730 | 92473 / 92473 | -12743 | -12743 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 4240 / 4240 | 4620 / 4620 | -380 | -380 |
| cache_creation_input_tokens | 31398 / 31398 | 20594 / 20594 | +10804 | +10804 |
| cache_read_input_tokens | 209337 / 209337 | 262274 / 262274 | -52937 | -52937 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
