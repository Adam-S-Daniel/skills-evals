# Eval report: debug-github-workflows

- Timestamp: 20261110T002212Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T001816Z-faf04f; started 2026-11-10T00:22:12Z, ended 2026-11-10T00:23:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.09, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 4.8 (4.8 to 4.8, 1 judged) | 0.1367 / 0.1367 |
| without_skill | 1 | 0 | 6/8 | 6.8 (6.8 to 6.8, 1 judged) | 0.0812 / 0.0812 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1367 / 0.1367 | 0.0812 / 0.0812 | +0.0555 | +0.0555 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 23351 / 23351 | 25377 / 25377 | -2026 | -2026 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 1633 / 1633 | 1738 / 1738 | -105 | -105 |
| cache_creation_input_tokens | 39360 / 39360 | 14282 / 14282 | +25078 | +25078 |
| cache_read_input_tokens | 219616 / 219616 | 281228 / 281228 | -61612 | -61612 |
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
