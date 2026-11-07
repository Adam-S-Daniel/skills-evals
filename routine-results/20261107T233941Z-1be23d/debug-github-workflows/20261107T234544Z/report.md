# Eval report: debug-github-workflows

- Timestamp: 20261107T234544Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T233941Z-1be23d; started 2026-11-07T23:45:44Z, ended 2026-11-07T23:47:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.24, judge $0.10, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.1355 / 0.1355 |
| without_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1001 / 0.1001 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1355 / 0.1355 | 0.1001 / 0.1001 | +0.0353 | +0.0353 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 21231 / 21231 | 28907 / 28907 | -7676 | -7676 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 1724 / 1724 | 2113 / 2113 | -389 | -389 |
| cache_creation_input_tokens | 24669 / 24669 | 13656 / 13656 | +11013 | +11013 |
| cache_read_input_tokens | 195281 / 195281 | 243450 / 243450 | -48169 | -48169 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
