# Eval report: debug-github-workflows

- Timestamp: 20261108T092936Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T092401Z-1f3ec3; started 2026-11-08T09:29:36Z, ended 2026-11-08T09:31:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.26, judge $0.10, guard $0.00; last agent call $0.12

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1457 / 0.1457 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1174 / 0.1174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1457 / 0.1457 | 0.1174 / 0.1174 | +0.0283 | +0.0283 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 29944 / 29944 | 35636 / 35636 | -5692 | -5692 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2324 / 2324 | 3253 / 3253 | -929 | -929 |
| cache_creation_input_tokens | 24774 / 24774 | 15082 / 15082 | +9692 | +9692 |
| cache_read_input_tokens | 232998 / 232998 | 245087 / 245087 | -12089 | -12089 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
