# Eval report: debug-github-workflows

- Timestamp: 20261107T091104Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T091009Z-c11a6b; started 2026-11-07T09:11:04Z, ended 2026-11-07T09:13:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.45 over 6 call(s); agent $0.30, judge $0.15, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.3/7 | 8.2 (8.2 to 8.2, 3 judged) | 0.0985 / 0.2955 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0985 / 0.0995 |
| num_turns | 7 / 8 |
| duration_ms | 31977.3 / 28469 |
| input_tokens | 14 / 16 |
| output_tokens | 2028.3 / 2052 |
| cache_creation_input_tokens | 13056 / 12320 |
| cache_read_input_tokens | 259620.7 / 296837 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| no-remote-write | 3/3 |
| working-listing-syncs-every-label | 3/3 |
| failed-listing-fails-the-script | 3/3 |
| reply-names-the-swallowing-construct | 1/3 |
| reply-names-the-missing-flag | 3/3 |
| workflow-and-inputs-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
