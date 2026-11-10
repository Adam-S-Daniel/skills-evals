# Eval report: debug-github-workflows

- Timestamp: 20261110T034232Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T034012Z-b5dbff; started 2026-11-10T03:42:32Z, ended 2026-11-10T03:44:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 4 call(s); agent $0.59, judge $0.14, guard $0.00; last agent call $0.23

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.3556 / 0.3556 |
| without_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.2339 / 0.2339 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3556 / 0.3556 | 0.2339 / 0.2339 | +0.1218 | +0.1218 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 51504 / 51504 | 49442 / 49442 | +2062 | +2062 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 3207 / 3207 | 3182 / 3182 | +25 | +25 |
| cache_creation_input_tokens | 46010 / 46010 | 21020 / 21020 | +24990 | +24990 |
| cache_read_input_tokens | 276926 / 276926 | 304232 / 304232 | -27306 | -27306 |
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
