# Eval report: debug-github-workflows

- Timestamp: 20261104T040937Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T040656Z-09a7b2; started 2026-11-04T04:09:37Z, ended 2026-11-04T04:11:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.91 to 0.91, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.23, judge $0.17, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1409 / 0.1409 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0899 / 0.0899 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1409 / 0.1409 | 0.0899 / 0.0899 | +0.0510 | +0.0510 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 26608 / 26608 | 26019 / 26019 | +589 | +589 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 2227 / 2227 | 1804 / 1804 | +423 | +423 |
| cache_creation_input_tokens | 23866 / 23866 | 12811 / 12811 | +11055 | +11055 |
| cache_read_input_tokens | 231681 / 231681 | 206219 / 206219 | +25462 | +25462 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
