# Eval report: debug-github-workflows

- Timestamp: 20261108T092539Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T092401Z-1f3ec3; started 2026-11-08T09:25:39Z, ended 2026-11-08T09:29:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.34 over 4 call(s); agent $0.99, judge $0.35, guard $0.00; last agent call $0.44

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.5471 / 0.5471 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4425 / 0.4425 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5471 / 0.5471 | 0.4425 / 0.4425 | +0.1046 | +0.1046 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 94885 / 94885 | 95443 / 95443 | -558 | -558 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4967 / 4967 | 4746 / 4746 | +221 | +221 |
| cache_creation_input_tokens | 32464 / 32464 | 22024 / 22024 | +10440 | +10440 |
| cache_read_input_tokens | 207591 / 207591 | 219504 / 219504 | -11913 | -11913 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
