# Eval report: debug-github-workflows

- Timestamp: 20261108T113553Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T113358Z-628707; started 2026-11-08T11:35:53Z, ended 2026-11-08T11:39:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.20 over 4 call(s); agent $0.83, judge $0.37, guard $0.00; last agent call $0.42

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4137 / 0.4137 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4157 / 0.4157 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4137 / 0.4137 | 0.4157 / 0.4157 | -0.0019 | -0.0019 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 108869 / 108869 | 76907 / 76907 | +31962 | +31962 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 4646 / 4646 | 3887 / 3887 | +759 | +759 |
| cache_creation_input_tokens | 32079 / 32079 | 19640 / 19640 | +12439 | +12439 |
| cache_read_input_tokens | 256008 / 256008 | 216402 / 216402 | +39606 | +39606 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 1/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
