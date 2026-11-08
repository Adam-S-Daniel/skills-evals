# Eval report: debug-github-workflows

- Timestamp: 20261108T101310Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T101121Z-f51ec9; started 2026-11-08T10:13:10Z, ended 2026-11-08T10:15:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 2 call(s); agent $0.91, judge $0.00, guard $0.00; last agent call $0.41

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.5017 / 0.5017 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.4121 / 0.4121 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5017 / 0.5017 | 0.4121 / 0.4121 | +0.0896 | +0.0896 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 80842 / 80842 | 84312 / 84312 | -3470 | -3470 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4361 / 4361 | 4656 / 4656 | -295 | -295 |
| cache_creation_input_tokens | 30288 / 30288 | 21111 / 21111 | +9177 | +9177 |
| cache_read_input_tokens | 203683 / 203683 | 217010 / 217010 | -13327 | -13327 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 0/1 |
| instrument-unchanged | 1/1 | 1/1 |
