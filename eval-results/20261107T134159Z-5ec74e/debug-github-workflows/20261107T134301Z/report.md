# Eval report: debug-github-workflows

- Timestamp: 20261107T134301Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T134159Z-5ec74e; started 2026-11-07T13:43:01Z, ended 2026-11-07T13:45:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 6 call(s); agent $0.59, judge $0.43, guard $0.00; last agent call $0.20

## Fixture: secret-name (n=3)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.7/8 | 7.8 (7.4 to 8.2, 3 judged) | 0.1981 / 0.5942 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1981 / 0.1990 |
| num_turns | 7.3 / 7 |
| duration_ms | 31486.7 / 35518 |
| input_tokens | 14.7 / 14 |
| output_tokens | 1839.7 / 1811 |
| cache_creation_input_tokens | 13294.3 / 13765 |
| cache_read_input_tokens | 274232 / 263220 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| run-log-read-without-writes | 1/3 |
| secret-names-listed | 1/3 |
| workflow-reads-the-existing-secret | 3/3 |
| workflows-still-parse | 3/3 |
| permissions-stay-read-only | 3/3 |
| reply-names-both-secrets | 3/3 |
| everything-else-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
