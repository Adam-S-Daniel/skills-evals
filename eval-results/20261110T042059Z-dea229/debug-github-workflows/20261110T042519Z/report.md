# Eval report: debug-github-workflows

- Timestamp: 20261110T042519Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T042059Z-dea229; started 2026-11-10T04:25:19Z, ended 2026-11-10T04:26:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.24, judge $0.10, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1457 / 0.1457 |
| without_skill | 1 | 0 | 8/8 | 8.4 (8.4 to 8.4, 1 judged) | 0.0908 / 0.0908 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1457 / 0.1457 | 0.0908 / 0.0908 | +0.0549 | +0.0549 |
| num_turns | 9 / 9 | 10 / 10 | -1 | -1 |
| duration_ms | 31177 / 31177 | 35273 / 35273 | -4096 | -4096 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 1973 / 1973 | 1992 / 1992 | -19 | -19 |
| cache_creation_input_tokens | 40136 / 40136 | 15500 / 15500 | +24636 | +24636 |
| cache_read_input_tokens | 256456 / 256456 | 321289 / 321289 | -64833 | -64833 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
