# Eval report: debug-github-workflows

- Timestamp: 20261110T005628Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T005207Z-07029f; started 2026-11-10T00:56:28Z, ended 2026-11-10T00:57:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1419 / 0.1419 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0748 / 0.0748 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1419 / 0.1419 | 0.0748 / 0.0748 | +0.0671 | +0.0671 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 27663 / 27663 | 23132 / 23132 | +4531 | +4531 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 1827 / 1827 | 1613 / 1613 | +214 | +214 |
| cache_creation_input_tokens | 39164 / 39164 | 13699 / 13699 | +25465 | +25465 |
| cache_read_input_tokens | 256817 / 256817 | 243923 / 243923 | +12894 | +12894 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 1/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 0/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 0/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
