# Eval report: debug-github-workflows

- Timestamp: 20261103T151227Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T151029Z-8823cf; started 2026-11-03T15:12:27Z, ended 2026-11-03T15:13:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1568 / 0.1568 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.1088 / 0.1088 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1568 / 0.1568 | 0.1088 / 0.1088 | +0.0481 | +0.0481 |
| num_turns | 11 / 11 | 9 / 9 | +2 | +2 |
| duration_ms | 39017 / 39017 | 32952 / 32952 | +6065 | +6065 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 2249 / 2249 | 2021 / 2021 | +228 | +228 |
| cache_creation_input_tokens | 24984 / 24984 | 15081 / 15081 | +9903 | +9903 |
| cache_read_input_tokens | 343765 / 343765 | 282222 / 282222 | +61543 | +61543 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
