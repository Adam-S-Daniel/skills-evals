# Eval report: debug-github-workflows

- Timestamp: 20261110T045614Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T045411Z-8fa01a; started 2026-11-10T04:56:14Z, ended 2026-11-10T04:57:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.19, judge $0.09, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.6 (8.6 to 8.6, 1 judged) | 0.1077 / 0.1077 |
| without_skill | 1 | 0 | 8/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.0826 / 0.0826 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1077 / 0.1077 | 0.0826 / 0.0826 | +0.0251 | +0.0251 |
| num_turns | 9 / 9 | 9 / 9 | 0 | 0 |
| duration_ms | 29828 / 29828 | 29044 / 29044 | +784 | +784 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1916 / 1916 | 1920 / 1920 | -4 | -4 |
| cache_creation_input_tokens | 24529 / 24529 | 14058 / 14058 | +10471 | +10471 |
| cache_read_input_tokens | 271804 / 271804 | 281979 / 281979 | -10175 | -10175 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 1/1 |
| secret-names-listed | 1/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
