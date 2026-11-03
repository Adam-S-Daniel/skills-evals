# Eval report: debug-github-workflows

- Timestamp: 20261103T161805Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T161054Z-e5f3a0; started 2026-11-03T16:18:05Z, ended 2026-11-03T16:20:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.65 over 2 call(s); agent $0.65, judge $0.00, guard $0.00; last agent call $0.27

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.3861 / 0.3861 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.2668 / 0.2668 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3861 / 0.3861 | 0.2668 / 0.2668 | +0.1192 | +0.1192 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 72614 / 72614 | 44722 / 44722 | +27892 | +27892 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 4029 / 4029 | 3585 / 3585 | +444 | +444 |
| cache_creation_input_tokens | 30954 / 30954 | 17969 / 17969 | +12985 | +12985 |
| cache_read_input_tokens | 288879 / 288879 | 256555 / 256555 | +32324 | +32324 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
