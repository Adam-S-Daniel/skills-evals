# Eval report: debug-github-workflows

- Timestamp: 20261108T101600Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T101121Z-f51ec9; started 2026-11-08T10:16:00Z, ended 2026-11-08T10:17:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.24, judge $0.09, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.1418 / 0.1418 |
| without_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0940 / 0.0940 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1418 / 0.1418 | 0.0940 / 0.0940 | +0.0478 | +0.0478 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 27395 / 27395 | 26244 / 26244 | +1151 | +1151 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2451 / 2451 | 1774 / 1774 | +677 | +677 |
| cache_creation_input_tokens | 24381 / 24381 | 14735 / 14735 | +9646 | +9646 |
| cache_read_input_tokens | 197195 / 197195 | 173123 / 173123 | +24072 | +24072 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
