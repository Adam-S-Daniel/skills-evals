# Eval report: debug-github-workflows

- Timestamp: 20261107T234120Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T233941Z-1be23d; started 2026-11-07T23:41:20Z, ended 2026-11-07T23:45:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.38 over 4 call(s); agent $1.08, judge $0.30, guard $0.00; last agent call $0.54

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.5466 / 0.5466 |
| without_skill | 1 | 0 | 6/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.5363 / 0.5363 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5466 / 0.5466 | 0.5363 / 0.5363 | +0.0104 | +0.0104 |
| num_turns | 6 / 6 | 10 / 10 | -4 | -4 |
| duration_ms | 82409 / 82409 | 143537 / 143537 | -61128 | -61128 |
| input_tokens | 14 / 14 | 26 / 26 | -12 | -12 |
| output_tokens | 5124 / 5124 | 6009 / 6009 | -885 | -885 |
| cache_creation_input_tokens | 31966 / 31966 | 25901 / 25901 | +6065 | +6065 |
| cache_read_input_tokens | 208416 / 208416 | 407869 / 407869 | -199453 | -199453 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 0/1 |
| instrument-unchanged | 1/1 | 1/1 |
