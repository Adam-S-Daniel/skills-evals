# Eval report: debug-github-workflows

- Timestamp: 20261107T092522Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T092421Z-afda7d; started 2026-11-07T09:25:22Z, ended 2026-11-07T09:27:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 6 call(s); agent $0.33, judge $0.13, guard $0.00; last agent call $0.11

## Fixture: secret-name (n=3)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.3/8 | 7.0 (5.0 to 8.0, 3 judged) | 0.1111 / 0.3334 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1111 / 0.1100 |
| num_turns | 10.7 / 11 |
| duration_ms | 33284.3 / 32661 |
| input_tokens | 21.3 / 22 |
| output_tokens | 2063.3 / 1996 |
| cache_creation_input_tokens | 12694 / 12796 |
| cache_read_input_tokens | 396919.7 / 407833 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| run-log-read-without-writes | 2/3 |
| secret-names-listed | 2/3 |
| workflow-reads-the-existing-secret | 3/3 |
| workflows-still-parse | 3/3 |
| permissions-stay-read-only | 3/3 |
| reply-names-both-secrets | 3/3 |
| everything-else-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
