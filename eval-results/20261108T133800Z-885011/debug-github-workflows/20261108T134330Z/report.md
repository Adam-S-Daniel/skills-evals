# Eval report: debug-github-workflows

- Timestamp: 20261108T134330Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T133800Z-885011; started 2026-11-08T13:43:30Z, ended 2026-11-08T13:44:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.77, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1420 / 0.1420 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1014 / 0.1014 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1420 / 0.1420 | 0.1014 / 0.1014 | +0.0406 | +0.0406 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 31611 / 31611 | 29527 / 29527 | +2084 | +2084 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2062 / 2062 | 2257 / 2257 | -195 | -195 |
| cache_creation_input_tokens | 24481 / 24481 | 13617 / 13617 | +10864 | +10864 |
| cache_read_input_tokens | 233831 / 233831 | 242971 / 242971 | -9140 | -9140 |
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
