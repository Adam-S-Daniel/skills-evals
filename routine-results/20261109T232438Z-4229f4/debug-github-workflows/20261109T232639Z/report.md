# Eval report: debug-github-workflows

- Timestamp: 20261109T232639Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T232438Z-4229f4; started 2026-11-09T23:26:39Z, ended 2026-11-09T23:29:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.96 over 4 call(s); agent $0.74, judge $0.22, guard $0.00; last agent call $0.25

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4901 / 0.4901 |
| without_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.2487 / 0.2487 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4901 / 0.4901 | 0.2487 / 0.2487 | +0.2414 | +0.2414 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 74882 / 74882 | 50239 / 50239 | +24643 | +24643 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 4324 / 4324 | 5223 / 5223 | -899 | -899 |
| cache_creation_input_tokens | 45864 / 45864 | 18550 / 18550 | +27314 | +27314 |
| cache_read_input_tokens | 237613 / 237613 | 257187 / 257187 | -19574 | -19574 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 0/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
