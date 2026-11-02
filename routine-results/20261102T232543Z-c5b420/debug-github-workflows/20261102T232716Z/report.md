# Eval report: debug-github-workflows

- Timestamp: 20261102T232716Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261102T232543Z-c5b420; started 2026-11-02T23:27:16Z, ended 2026-11-02T23:29:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.24, judge $0.16, guard $0.00; last agent call $0.10

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 7.8 (7.8 to 7.8, 1 judged) | 0.1366 / 0.1366 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1031 / 0.1031 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1366 / 0.1366 | 0.1031 / 0.1031 | +0.0335 | +0.0335 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 25150 / 25150 | 26425 / 26425 | -1275 | -1275 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 1691 / 1691 | 2116 / 2116 | -425 | -425 |
| cache_creation_input_tokens | 25013 / 25013 | 14363 / 14363 | +10650 | +10650 |
| cache_read_input_tokens | 196044 / 196044 | 244680 / 244680 | -48636 | -48636 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-remote-write | 1/1 | 1/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
