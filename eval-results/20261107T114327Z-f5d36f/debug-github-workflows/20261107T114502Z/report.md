# Eval report: debug-github-workflows

- Timestamp: 20261107T114502Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T114327Z-f5d36f; started 2026-11-07T11:45:02Z, ended 2026-11-07T11:47:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 4 call(s); agent $0.46, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=2)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/8 | skipped (objective-decided) | 0.1286 / 0.2572 |
| without_skill | 2 | 0 | 5.5/8 | skipped (objective-decided) | 0.0995 / 0.1991 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1286 / 0.1286 | 0.0995 / 0.0995 | +0.0290 | +0.0290 |
| num_turns | 8.5 / 8.5 | 8 / 8 | +0.5 | +0.5 |
| duration_ms | 29073.5 / 29073.5 | 30119 / 30119 | -1045.5 | -1045.5 |
| input_tokens | 16 / 16 | 15 / 15 | +1 | +1 |
| output_tokens | 1789 / 1789 | 1788 / 1788 | +1 | +1 |
| cache_creation_input_tokens | 20688.5 / 20688.5 | 13919 / 13919 | +6769.5 | +6769.5 |
| cache_read_input_tokens | 279003 / 279003 | 259410 / 259410 | +19593 | +19593 |
| tool_errors | 0.5 / 0.5 | 0 / 0 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/2 | 1/2 |
| secret-names-listed | 1/2 | 0/2 |
| workflow-reads-the-existing-secret | 2/2 | 1/2 |
| workflows-still-parse | 2/2 | 2/2 |
| permissions-stay-read-only | 2/2 | 2/2 |
| reply-names-both-secrets | 2/2 | 1/2 |
| everything-else-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
