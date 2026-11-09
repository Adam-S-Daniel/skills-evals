# Eval report: debug-github-workflows

- Timestamp: 20261109T222524Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T222314Z-df4eb4; started 2026-11-09T22:25:24Z, ended 2026-11-09T22:28:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.05 over 4 call(s); agent $0.84, judge $0.22, guard $0.00; last agent call $0.37

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4628 / 0.4628 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.3734 / 0.3734 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4628 / 0.4628 | 0.3734 / 0.3734 | +0.0894 | +0.0894 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 60487 / 60487 | 87020 / 87020 | -26533 | -26533 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3907 / 3907 | 4709 / 4709 | -802 | -802 |
| cache_creation_input_tokens | 44942 / 44942 | 20633 / 20633 | +24309 | +24309 |
| cache_read_input_tokens | 190430 / 190430 | 260509 / 260509 | -70079 | -70079 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
