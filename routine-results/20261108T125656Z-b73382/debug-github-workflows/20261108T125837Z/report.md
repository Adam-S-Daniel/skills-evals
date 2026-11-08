# Eval report: debug-github-workflows

- Timestamp: 20261108T125837Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T125656Z-b73382; started 2026-11-08T12:58:37Z, ended 2026-11-08T13:02:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.39 over 4 call(s); agent $1.02, judge $0.36, guard $0.00; last agent call $0.44

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.5848 / 0.5848 |
| without_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.4400 / 0.4400 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5848 / 0.5848 | 0.4400 / 0.4400 | +0.1448 | +0.1448 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 105198 / 105198 | 86782 / 86782 | +18416 | +18416 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 5084 / 5084 | 4961 / 4961 | +123 | +123 |
| cache_creation_input_tokens | 34320 / 34320 | 20596 / 20596 | +13724 | +13724 |
| cache_read_input_tokens | 298161 / 298161 | 301709 / 301709 | -3548 | -3548 |
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
