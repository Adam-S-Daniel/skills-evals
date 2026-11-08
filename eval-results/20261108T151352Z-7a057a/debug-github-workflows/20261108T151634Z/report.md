# Eval report: debug-github-workflows

- Timestamp: 20261108T151634Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T151352Z-7a057a; started 2026-11-08T15:16:34Z, ended 2026-11-08T15:20:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.22 over 4 call(s); agent $0.89, judge $0.32, guard $0.00; last agent call $0.39

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.5044 / 0.5044 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.3888 / 0.3888 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5044 / 0.5044 | 0.3888 / 0.3888 | +0.1155 | +0.1155 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 98955 / 98955 | 81613 / 81613 | +17342 | +17342 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4506 / 4506 | 4210 / 4210 | +296 | +296 |
| cache_creation_input_tokens | 30458 / 30458 | 20169 / 20169 | +10289 | +10289 |
| cache_read_input_tokens | 202760 / 202760 | 214400 / 214400 | -11640 | -11640 |
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
