# Eval report: debug-github-workflows

- Timestamp: 20261108T182651Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T182459Z-75d0f3; started 2026-11-08T18:26:51Z, ended 2026-11-08T18:29:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 2 call(s); agent $0.70, judge $0.00, guard $0.00; last agent call $0.37

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3321 / 0.3321 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3687 / 0.3687 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3321 / 0.3321 | 0.3687 / 0.3687 | -0.0366 | -0.0366 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 55626 / 55626 | 89802 / 89802 | -34176 | -34176 |
| input_tokens | 12 / 12 | 16 / 16 | -4 | -4 |
| output_tokens | 4143 / 4143 | 4242 / 4242 | -99 | -99 |
| cache_creation_input_tokens | 42253 / 42253 | 20935 / 20935 | +21318 | +21318 |
| cache_read_input_tokens | 189719 / 189719 | 263016 / 263016 | -73297 | -73297 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 0/1 |
| instrument-unchanged | 1/1 | 1/1 |
