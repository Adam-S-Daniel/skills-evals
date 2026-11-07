# Eval report: debug-github-workflows

- Timestamp: 20261107T114840Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T114705Z-bdf086; started 2026-11-07T11:48:40Z, ended 2026-11-07T11:51:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.59 over 8 call(s); agent $0.41, judge $0.19, guard $0.00; last agent call $0.09

## Fixture: swallowed-failure (n=2)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | 7.7 (6.6 to 8.8, 2 judged) | 0.1170 / 0.2340 |
| without_skill | 2 | 0 | 7/7 | 8.6 (8.2 to 9.0, 2 judged) | 0.0858 / 0.1717 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1170 / 0.1170 | 0.0858 / 0.0858 | +0.0311 | +0.0311 |
| num_turns | 6.5 / 6.5 | 5 / 5 | +1.5 | +1.5 |
| duration_ms | 27393.5 / 27393.5 | 19932 / 19932 | +7461.5 | +7461.5 |
| input_tokens | 13 / 13 | 10 / 10 | +3 | +3 |
| output_tokens | 2035 / 2035 | 1705.5 / 1705.5 | +329.5 | +329.5 |
| cache_creation_input_tokens | 18688 / 18688 | 12985 / 12985 | +5703 | +5703 |
| cache_read_input_tokens | 218667 / 218667 | 168339 / 168339 | +50328 | +50328 |
| tool_errors | 0.5 / 0.5 | 0 / 0 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 2/2 | 2/2 |
| working-listing-syncs-every-label | 2/2 | 2/2 |
| failed-listing-fails-the-script | 2/2 | 2/2 |
| reply-names-the-swallowing-construct | 2/2 | 2/2 |
| reply-names-the-missing-flag | 2/2 | 2/2 |
| workflow-and-inputs-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
