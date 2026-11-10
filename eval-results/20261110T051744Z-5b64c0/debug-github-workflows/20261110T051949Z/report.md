# Eval report: debug-github-workflows

- Timestamp: 20261110T051949Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T051744Z-5b64c0; started 2026-11-10T05:19:49Z, ended 2026-11-10T05:21:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.23, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/8 | 3.4 (3.4 to 3.4, 1 judged) | 0.1429 / 0.1429 |
| without_skill | 1 | 0 | 8/8 | 7.0 (7.0 to 7.0, 1 judged) | 0.0831 / 0.0831 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1429 / 0.1429 | 0.0831 / 0.0831 | +0.0598 | +0.0598 |
| num_turns | 8 / 8 | 9 / 9 | -1 | -1 |
| duration_ms | 33368 / 33368 | 29054 / 29054 | +4314 | +4314 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1971 / 1971 | 1978 / 1978 | -7 | -7 |
| cache_creation_input_tokens | 39011 / 39011 | 14068 / 14068 | +24943 | +24943 |
| cache_read_input_tokens | 256455 / 256455 | 281251 / 281251 | -24796 | -24796 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 1/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 0/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 0/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
