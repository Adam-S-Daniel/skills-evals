# Eval report: debug-github-workflows

- Timestamp: 20261108T010941Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T010748Z-cb2776; started 2026-11-08T01:09:41Z, ended 2026-11-08T01:12:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.92 over 2 call(s); agent $0.92, judge $0.00, guard $0.00; last agent call $0.39

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.5309 / 0.5309 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3873 / 0.3873 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5309 / 0.5309 | 0.3873 / 0.3873 | +0.1436 | +0.1436 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 89096 / 89096 | 77350 / 77350 | +11746 | +11746 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 5003 / 5003 | 4479 / 4479 | +524 | +524 |
| cache_creation_input_tokens | 32097 / 32097 | 19702 / 19702 | +12395 | +12395 |
| cache_read_input_tokens | 206585 / 206585 | 257418 / 257418 | -50833 | -50833 |
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
