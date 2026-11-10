# Eval report: debug-github-workflows

- Timestamp: 20261110T005436Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T005207Z-07029f; started 2026-11-10T00:54:36Z, ended 2026-11-10T00:56:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 4 call(s); agent $0.56, judge $0.15, guard $0.00; last agent call $0.23

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.3318 / 0.3318 |
| without_skill | 1 | 0 | 6/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.2325 / 0.2325 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3318 / 0.3318 | 0.2325 / 0.2325 | +0.0993 | +0.0993 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 35751 / 35751 | 56072 / 56072 | -20321 | -20321 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 2928 / 2928 | 3582 / 3582 | -654 | -654 |
| cache_creation_input_tokens | 45257 / 45257 | 19142 / 19142 | +26115 | +26115 |
| cache_read_input_tokens | 234515 / 234515 | 295645 / 295645 | -61130 | -61130 |
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
