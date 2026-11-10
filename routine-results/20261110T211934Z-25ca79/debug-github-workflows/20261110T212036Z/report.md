# Eval report: debug-github-workflows

- Timestamp: 20261110T212036Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T211934Z-25ca79; started 2026-11-10T21:20:36Z, ended 2026-11-10T21:22:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.28, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 6 call(s); agent $0.63, judge $0.27, guard $0.00; last agent call $0.17

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.7/7 | 8.2 (8.0 to 8.6, 3 judged) | 0.2103 / 0.6308 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2103 / 0.1679 |
| num_turns | 6 / 6 |
| duration_ms | 29074.7 / 29339 |
| input_tokens | 12 / 12 |
| output_tokens | 2629.3 / 2611 |
| cache_creation_input_tokens | 22987.7 / 13599 |
| cache_read_input_tokens | 213472.3 / 222627 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| no-remote-write | 3/3 |
| working-listing-syncs-every-label | 3/3 |
| failed-listing-fails-the-script | 3/3 |
| reply-names-the-swallowing-construct | 2/3 |
| reply-names-the-missing-flag | 3/3 |
| workflow-and-inputs-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
