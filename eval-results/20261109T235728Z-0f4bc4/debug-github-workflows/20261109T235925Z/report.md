# Eval report: debug-github-workflows

- Timestamp: 20261109T235925Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T235728Z-0f4bc4; started 2026-11-09T23:59:25Z, ended 2026-11-10T00:02:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 4 call(s); agent $0.67, judge $0.22, guard $0.00; last agent call $0.34

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.3316 / 0.3316 |
| without_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.3358 / 0.3358 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3316 / 0.3316 | 0.3358 / 0.3358 | -0.0042 | -0.0042 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 118452 / 118452 | 61216 / 61216 | +57236 | +57236 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 4914 / 4914 | 3628 / 3628 | +1286 | +1286 |
| cache_creation_input_tokens | 32280 / 32280 | 18982 / 18982 | +13298 | +13298 |
| cache_read_input_tokens | 293875 / 293875 | 215392 / 215392 | +78483 | +78483 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 0/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
