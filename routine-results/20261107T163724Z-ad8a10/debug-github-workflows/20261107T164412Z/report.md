# Eval report: debug-github-workflows

- Timestamp: 20261107T164412Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T163724Z-ad8a10; started 2026-11-07T16:44:12Z, ended 2026-11-07T16:47:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.55, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 6 call(s); agent $0.67, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: secret-name (n=3)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1174 / 0.3521 |
| without_skill | 3 | 0 | 6.3/8 | skipped (objective-decided) | 0.1051 / 0.3152 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1174 / 0.1102 | 0.1051 / 0.1052 | +0.0123 | +0.0050 |
| num_turns | 8.3 / 8 | 8.3 / 8 | 0 | 0 |
| duration_ms | 29837.7 / 29736 | 36045.3 / 36463 | -6207.7 | -6727 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1754.3 / 1754 | 1930.7 / 1983 | -176.3 | -229 |
| cache_creation_input_tokens | 18015.3 / 14728 | 14438.3 / 14313 | +3577 | +415 |
| cache_read_input_tokens | 277237 / 269566 | 279745 / 280522 | -2508 | -10956 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/3 | 2/3 |
| secret-names-listed | 1/3 | 1/3 |
| workflow-reads-the-existing-secret | 3/3 | 2/3 |
| workflows-still-parse | 3/3 | 3/3 |
| permissions-stay-read-only | 3/3 | 3/3 |
| reply-names-both-secrets | 3/3 | 2/3 |
| everything-else-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
