# Eval report: debug-github-workflows

- Timestamp: 20261108T122033Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T121539Z-509ab5; started 2026-11-08T12:20:33Z, ended 2026-11-08T12:21:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.24, judge $0.10, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1422 / 0.1422 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0967 / 0.0967 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1422 / 0.1422 | 0.0967 / 0.0967 | +0.0455 | +0.0455 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 27656 / 27656 | 23481 / 23481 | +4175 | +4175 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 2213 / 2213 | 1996 / 1996 | +217 | +217 |
| cache_creation_input_tokens | 24130 / 24130 | 13998 / 13998 | +10132 | +10132 |
| cache_read_input_tokens | 234899 / 234899 | 207286 / 207286 | +27613 | +27613 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
