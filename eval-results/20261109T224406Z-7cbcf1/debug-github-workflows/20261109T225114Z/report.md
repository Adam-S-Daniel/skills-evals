# Eval report: debug-github-workflows

- Timestamp: 20261109T225114Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T224406Z-7cbcf1; started 2026-11-09T22:51:14Z, ended 2026-11-09T22:52:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 2 call(s); agent $0.21, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.1431 / 0.1431 |
| without_skill | 1 | 0 | 4/8 | skipped (objective-decided) | 0.0670 / 0.0670 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1431 / 0.1431 | 0.0670 / 0.0670 | +0.0762 | +0.0762 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 33787 / 33787 | 37462 / 37462 | -3675 | -3675 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 1829 / 1829 | 1523 / 1523 | +306 | +306 |
| cache_creation_input_tokens | 39657 / 39657 | 12515 / 12515 | +27142 | +27142 |
| cache_read_input_tokens | 256819 / 256819 | 204520 / 204520 | +52299 | +52299 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 0/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 0/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
