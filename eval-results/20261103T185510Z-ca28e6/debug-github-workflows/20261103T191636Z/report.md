# Eval report: debug-github-workflows

- Timestamp: 20261103T191636Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T185510Z-ca28e6; started 2026-11-03T19:16:36Z, ended 2026-11-03T19:19:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.07 over 4 call(s); agent $0.64, judge $0.43, guard $0.00; last agent call $0.30

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.3383 / 0.3383 |
| without_skill | 1 | 0 | 6/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.3006 / 0.3006 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3383 / 0.3383 | 0.3006 / 0.3006 | +0.0376 | +0.0376 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 46727 / 46727 | 68726 / 68726 | -21999 | -21999 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 2842 / 2842 | 3127 / 3127 | -285 | -285 |
| cache_creation_input_tokens | 28424 / 28424 | 21530 / 21530 | +6894 | +6894 |
| cache_read_input_tokens | 244145 / 244145 | 305013 / 305013 | -60868 | -60868 |
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
