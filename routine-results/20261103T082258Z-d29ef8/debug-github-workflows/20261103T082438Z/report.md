# Eval report: debug-github-workflows

- Timestamp: 20261103T082438Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T082258Z-d29ef8; started 2026-11-03T08:24:38Z, ended 2026-11-03T08:27:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.13 over 4 call(s); agent $0.60, judge $0.53, guard $0.00; last agent call $0.25

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 6.6 (6.6 to 6.6, 1 judged) | 0.3498 / 0.3498 |
| without_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.2456 / 0.2456 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3498 / 0.3498 | 0.2456 / 0.2456 | +0.1042 | +0.1042 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 38809 / 38809 | 31702 / 31702 | +7107 | +7107 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3228 / 3228 | 2923 / 2923 | +305 | +305 |
| cache_creation_input_tokens | 29529 / 29529 | 17984 / 17984 | +11545 | +11545 |
| cache_read_input_tokens | 244824 / 244824 | 216047 / 216047 | +28777 | +28777 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
