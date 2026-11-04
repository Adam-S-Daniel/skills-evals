# Eval report: debug-github-workflows

- Timestamp: 20261104T194610Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T194414Z-c55c3b; started 2026-11-04T19:46:10Z, ended 2026-11-04T19:47:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.05, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 4 call(s); agent $0.22, judge $0.17, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1213 / 0.1213 |
| without_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0955 / 0.0955 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1213 / 0.1213 | 0.0955 / 0.0955 | +0.0258 | +0.0258 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 24579 / 24579 | 18889 / 18889 | +5690 | +5690 |
| input_tokens | 8 / 8 | 12 / 12 | -4 | -4 |
| output_tokens | 1565 / 1565 | 2013 / 2013 | -448 | -448 |
| cache_creation_input_tokens | 23378 / 23378 | 13653 / 13653 | +9725 | +9725 |
| cache_read_input_tokens | 121383 / 121383 | 207142 / 207142 | -85759 | -85759 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
