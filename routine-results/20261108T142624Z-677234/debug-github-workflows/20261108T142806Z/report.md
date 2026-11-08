# Eval report: debug-github-workflows

- Timestamp: 20261108T142806Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T142624Z-677234; started 2026-11-08T14:28:06Z, ended 2026-11-08T14:31:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.22 over 4 call(s); agent $0.89, judge $0.33, guard $0.00; last agent call $0.40

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4958 / 0.4958 |
| without_skill | 1 | 0 | 5/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.3970 / 0.3970 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4958 / 0.4958 | 0.3970 / 0.3970 | +0.0988 | +0.0988 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 77677 / 77677 | 82608 / 82608 | -4931 | -4931 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3917 / 3917 | 4407 / 4407 | -490 | -490 |
| cache_creation_input_tokens | 30753 / 30753 | 20531 / 20531 | +10222 | +10222 |
| cache_read_input_tokens | 204530 / 204530 | 258750 / 258750 | -54220 | -54220 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 0/1 |
| instrument-unchanged | 1/1 | 1/1 |
