# Eval report: debug-github-workflows

- Timestamp: 20261103T210323Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T204554Z-3bf541; started 2026-11-03T21:03:23Z, ended 2026-11-03T21:05:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.25, judge $0.17, guard $0.00; last agent call $0.11

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1460 / 0.1460 |
| without_skill | 1 | 0 | 6/8 | 4.4 (4.4 to 4.4, 1 judged) | 0.1058 / 0.1058 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1460 / 0.1460 | 0.1058 / 0.1058 | +0.0402 | +0.0402 |
| num_turns | 8 / 8 | 9 / 9 | -1 | -1 |
| duration_ms | 41587 / 41587 | 44217 / 44217 | -2630 | -2630 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1862 / 1862 | 1887 / 1887 | -25 | -25 |
| cache_creation_input_tokens | 25081 / 25081 | 14742 / 14742 | +10339 | +10339 |
| cache_read_input_tokens | 269923 / 269923 | 278815 / 278815 | -8892 | -8892 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
