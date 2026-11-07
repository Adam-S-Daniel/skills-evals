# Eval report: debug-github-workflows

- Timestamp: 20261107T155933Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155800Z-53e094; started 2026-11-07T15:59:33Z, ended 2026-11-07T16:10:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.52, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.57 over 12 call(s); agent $2.59, judge $0.98, guard $0.00; last agent call $0.42

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | 8.7 (8.6 to 8.8, 3 judged) | 0.4522 / 1.3567 |
| without_skill | 3 | 0 | 6/7 | 8.5 (8.2 to 8.6, 3 judged) | 0.4099 / 1.2297 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4522 / 0.4091 | 0.4099 / 0.4067 | +0.0423 | +0.0024 |
| num_turns | 6.7 / 6 | 6 / 6 | +0.7 | 0 |
| duration_ms | 90655 / 85897 | 90865.3 / 93050 | -210.3 | -7153 |
| input_tokens | 15.3 / 14 | 14 / 14 | +1.3 | 0 |
| output_tokens | 4691.7 / 4394 | 4213.3 / 4347 | +478.3 | +47 |
| cache_creation_input_tokens | 24336.7 / 20762 | 19717.7 / 19590 | +4619 | +1172 |
| cache_read_input_tokens | 240703 / 215223 | 215893.3 / 215818 | +24809.7 | -595 |
| tool_errors | 0.3 / 0 | 1 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 3/3 | 3/3 |
| working-listing-syncs-every-label | 3/3 | 3/3 |
| failed-listing-fails-the-script | 3/3 | 3/3 |
| reply-names-the-swallowing-construct | 1/3 | 2/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 2/3 | 1/3 |
| instrument-unchanged | 3/3 | 3/3 |
