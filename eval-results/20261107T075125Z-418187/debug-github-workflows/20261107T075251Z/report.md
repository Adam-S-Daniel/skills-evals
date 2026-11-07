# Eval report: debug-github-workflows

- Timestamp: 20261107T075251Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T075125Z-418187; started 2026-11-07T07:52:51Z, ended 2026-11-07T07:54:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.25, judge $0.10, guard $0.00; last agent call $0.11

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.1434 / 0.1434 |
| without_skill | 1 | 0 | 8/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1113 / 0.1113 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1434 / 0.1434 | 0.1113 / 0.1113 | +0.0321 | +0.0321 |
| num_turns | 8 / 8 | 10 / 10 | -2 | -2 |
| duration_ms | 23130 / 23130 | 40906 / 40906 | -17776 | -17776 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 1715 / 1715 | 2124 / 2124 | -409 | -409 |
| cache_creation_input_tokens | 24827 / 24827 | 14572 / 14572 | +10255 | +10255 |
| cache_read_input_tokens | 269585 / 269585 | 317508 / 317508 | -47923 | -47923 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 1/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
