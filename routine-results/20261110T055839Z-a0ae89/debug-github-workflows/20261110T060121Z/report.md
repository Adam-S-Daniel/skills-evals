# Eval report: debug-github-workflows

- Timestamp: 20261110T060121Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T055839Z-a0ae89; started 2026-11-10T06:01:21Z, ended 2026-11-10T06:04:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.06 over 4 call(s); agent $0.85, judge $0.21, guard $0.00; last agent call $0.37

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4812 / 0.4812 |
| without_skill | 1 | 0 | 7/7 | 7.8 (7.8 to 7.8, 1 judged) | 0.3686 / 0.3686 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4812 / 0.4812 | 0.3686 / 0.3686 | +0.1127 | +0.1127 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 75074 / 75074 | 92326 / 92326 | -17252 | -17252 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3765 / 3765 | 4724 / 4724 | -959 | -959 |
| cache_creation_input_tokens | 46025 / 46025 | 20492 / 20492 | +25533 | +25533 |
| cache_read_input_tokens | 192934 / 192934 | 263732 / 263732 | -70798 | -70798 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
