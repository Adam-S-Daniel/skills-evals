# Eval report: debug-github-workflows

- Timestamp: 20261107T192802Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T191630Z-124fe6; started 2026-11-07T19:28:02Z, ended 2026-11-07T19:32:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.88 over 12 call(s); agent $0.61, judge $0.27, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | 8.6 (8.2 to 8.8, 3 judged) | 0.1102 / 0.3307 |
| without_skill | 3 | 0 | 6.7/7 | 8.1 (8.0 to 8.2, 3 judged) | 0.0933 / 0.2800 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1102 / 0.0942 | 0.0933 / 0.0922 | +0.0169 | +0.0020 |
| num_turns | 6 / 6 | 6.3 / 6 | -0.3 | 0 |
| duration_ms | 24913.7 / 23281 | 27416.3 / 29781 | -2502.7 | -6500 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 2021.7 / 1914 | 1909.7 / 1900 | +112 | +14 |
| cache_creation_input_tokens | 17698 / 13635 | 13409.3 / 13169 | +4288.7 | +466 |
| cache_read_input_tokens | 191947.7 / 202179 | 205674 / 204802 | -13726.3 | -2623 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 3/3 | 3/3 |
| working-listing-syncs-every-label | 3/3 | 3/3 |
| failed-listing-fails-the-script | 3/3 | 3/3 |
| reply-names-the-swallowing-construct | 2/3 | 2/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
