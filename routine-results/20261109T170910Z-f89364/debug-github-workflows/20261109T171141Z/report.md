# Eval report: debug-github-workflows

- Timestamp: 20261109T171141Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T170910Z-f89364; started 2026-11-09T17:11:41Z, ended 2026-11-09T17:13:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 2 call(s); agent $0.82, judge $0.00, guard $0.00; last agent call $0.35

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.4689 / 0.4689 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.3491 / 0.3491 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4689 / 0.4689 | 0.3491 / 0.3491 | +0.1198 | +0.1198 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 61436 / 61436 | 71598 / 71598 | -10162 | -10162 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 4255 / 4255 | 4390 / 4390 | -135 | -135 |
| cache_creation_input_tokens | 44776 / 44776 | 20576 / 20576 | +24200 | +24200 |
| cache_read_input_tokens | 189988 / 189988 | 256346 / 256346 | -66358 | -66358 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 0/1 |
| instrument-unchanged | 1/1 | 1/1 |
