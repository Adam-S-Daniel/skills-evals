# Eval report: debug-github-workflows

- Timestamp: 20261109T200235Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T195911Z-1a8fd4; started 2026-11-09T20:02:35Z, ended 2026-11-09T20:03:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.09, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.4 (8.4 to 8.4, 1 judged) | 0.1418 / 0.1418 |
| without_skill | 1 | 0 | 8/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.0812 / 0.0812 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1418 / 0.1418 | 0.0812 / 0.0812 | +0.0606 | +0.0606 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 25117 / 25117 | 23693 / 23693 | +1424 | +1424 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1893 / 1893 | 1844 / 1844 | +49 | +49 |
| cache_creation_input_tokens | 38880 / 38880 | 13841 / 13841 | +25039 | +25039 |
| cache_read_input_tokens | 256485 / 256485 | 281392 / 281392 | -24907 | -24907 |
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
