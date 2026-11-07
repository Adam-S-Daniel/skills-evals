# Eval report: debug-github-workflows

- Timestamp: 20261107T161038Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155800Z-53e094; started 2026-11-07T16:10:38Z, ended 2026-11-07T16:14:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.53, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.87 over 12 call(s); agent $0.60, judge $0.27, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | 8.5 (8.2 to 9.0, 3 judged) | 0.1097 / 0.3291 |
| without_skill | 3 | 0 | 6.7/7 | 8.1 (8.0 to 8.2, 3 judged) | 0.0914 / 0.2742 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1097 / 0.1009 | 0.0914 / 0.0925 | +0.0183 | +0.0084 |
| num_turns | 6.3 / 7 | 6.3 / 6 | 0 | +1 |
| duration_ms | 32677.7 / 28720 | 25717.3 / 26061 | +6960.3 | +2659 |
| input_tokens | 12.7 / 14 | 12 / 12 | +0.7 | +2 |
| output_tokens | 2089 / 2015 | 1765 / 1671 | +324 | +344 |
| cache_creation_input_tokens | 16830.7 / 13462 | 13293 / 13163 | +3537.7 | +299 |
| cache_read_input_tokens | 214578.3 / 232217 | 205600.3 / 205928 | +8978 | +26289 |
| tool_errors | 0.7 / 0 | 0.3 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 3/3 | 3/3 |
| working-listing-syncs-every-label | 3/3 | 3/3 |
| failed-listing-fails-the-script | 3/3 | 3/3 |
| reply-names-the-swallowing-construct | 1/3 | 2/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
