# Eval report: debug-github-workflows

- Timestamp: 20261110T063604Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T063329Z-8761ea; started 2026-11-10T06:36:04Z, ended 2026-11-10T06:39:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 4 call(s); agent $0.81, judge $0.22, guard $0.00; last agent call $0.33

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4786 / 0.4786 |
| without_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.3326 / 0.3326 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4786 / 0.4786 | 0.3326 / 0.3326 | +0.1460 | +0.1460 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 76584 / 76584 | 73358 / 73358 | +3226 | +3226 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4187 / 4187 | 4277 / 4277 | -90 | -90 |
| cache_creation_input_tokens | 45111 / 45111 | 19988 / 19988 | +25123 | +25123 |
| cache_read_input_tokens | 190682 / 190682 | 215980 / 215980 | -25298 | -25298 |
| tool_errors | 2 / 2 | 2 / 2 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
