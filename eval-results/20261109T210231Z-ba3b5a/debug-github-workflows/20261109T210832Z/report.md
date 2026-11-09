# Eval report: debug-github-workflows

- Timestamp: 20261109T210832Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T210231Z-ba3b5a; started 2026-11-09T21:08:32Z, ended 2026-11-09T21:09:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.24, judge $0.10, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1481 / 0.1481 |
| without_skill | 1 | 0 | 8/8 | 7.2 (7.2 to 7.2, 1 judged) | 0.0939 / 0.0939 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1481 / 0.1481 | 0.0939 / 0.0939 | +0.0542 | +0.0542 |
| num_turns | 9 / 9 | 9 / 9 | 0 | 0 |
| duration_ms | 25737 / 25737 | 30235 / 30235 | -4498 | -4498 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 1865 / 1865 | 2093 / 2093 | -228 | -228 |
| cache_creation_input_tokens | 39893 / 39893 | 16144 / 16144 | +23749 | +23749 |
| cache_read_input_tokens | 296359 / 296359 | 325306 / 325306 | -28947 | -28947 |
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
