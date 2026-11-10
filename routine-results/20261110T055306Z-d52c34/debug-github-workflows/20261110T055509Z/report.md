# Eval report: debug-github-workflows

- Timestamp: 20261110T055509Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T055306Z-d52c34; started 2026-11-10T05:55:09Z, ended 2026-11-10T05:57:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.23, judge $0.07, guard $0.00; last agent call $0.07

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.6 (9.6 to 9.6, 1 judged) | 0.1583 / 0.1583 |
| without_skill | 1 | 0 | 8/8 | 8.0 (8.0 to 8.0, 1 judged) | 0.0716 / 0.0716 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1583 / 0.1583 | 0.0716 / 0.0716 | +0.0867 | +0.0867 |
| num_turns | 11 / 11 | 7 / 7 | +4 | +4 |
| duration_ms | 72709 / 72709 | 25153 / 25153 | +47556 | +47556 |
| input_tokens | 20 / 20 | 14 / 14 | +6 | +6 |
| output_tokens | 2284 / 2284 | 1506 / 1506 | +778 | +778 |
| cache_creation_input_tokens | 40622 / 40622 | 12906 / 12906 | +27716 | +27716 |
| cache_read_input_tokens | 338275 / 338275 | 242493 / 242493 | +95782 | +95782 |
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
