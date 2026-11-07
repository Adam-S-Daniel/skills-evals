# Eval report: debug-github-workflows

- Timestamp: 20261107T191808Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T191630Z-124fe6; started 2026-11-07T19:18:08Z, ended 2026-11-07T19:28:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.34 over 12 call(s); agent $2.37, judge $0.97, guard $0.00; last agent call $0.26

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | 8.6 (8.6 to 8.6, 3 judged) | 0.4291 / 1.2874 |
| without_skill | 3 | 0 | 6.7/7 | 8.3 (7.8 to 8.6, 3 judged) | 0.3622 / 1.0865 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4291 / 0.3996 | 0.3622 / 0.4023 | +0.0670 | -0.0027 |
| num_turns | 6 / 6 | 6.3 / 6 | -0.3 | 0 |
| duration_ms | 82076 / 78795 | 71453.7 / 79585 | +10622.3 | -790 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4109 / 4127 | 4221 / 4231 | -112 | -104 |
| cache_creation_input_tokens | 24053.7 / 20563 | 19626 / 20900 | +4427.7 | -337 |
| cache_read_input_tokens | 213730 / 215315 | 230358 / 218396 | -16628 | -3081 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 3/3 | 3/3 |
| working-listing-syncs-every-label | 3/3 | 3/3 |
| failed-listing-fails-the-script | 3/3 | 3/3 |
| reply-names-the-swallowing-construct | 2/3 | 2/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 2/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
