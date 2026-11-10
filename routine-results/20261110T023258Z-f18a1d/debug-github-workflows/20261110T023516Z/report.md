# Eval report: debug-github-workflows

- Timestamp: 20261110T023516Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T023258Z-f18a1d; started 2026-11-10T02:35:16Z, ended 2026-11-10T02:37:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 4 call(s); agent $0.55, judge $0.20, guard $0.00; last agent call $0.21

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.3384 / 0.3384 |
| without_skill | 1 | 0 | 7/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.2078 / 0.2078 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3384 / 0.3384 | 0.2078 / 0.2078 | +0.1306 | +0.1306 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 49443 / 49443 | 37276 / 37276 | +12167 | +12167 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3270 / 3270 | 3120 / 3120 | +150 | +150 |
| cache_creation_input_tokens | 44053 / 44053 | 18800 / 18800 | +25253 | +25253 |
| cache_read_input_tokens | 234724 / 234724 | 256828 / 256828 | -22104 | -22104 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
