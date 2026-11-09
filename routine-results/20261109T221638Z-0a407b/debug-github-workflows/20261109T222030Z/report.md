# Eval report: debug-github-workflows

- Timestamp: 20261109T222030Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T221638Z-0a407b; started 2026-11-09T22:20:30Z, ended 2026-11-09T22:21:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1473 / 0.1473 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.0775 / 0.0775 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1473 / 0.1473 | 0.0775 / 0.0775 | +0.0697 | +0.0697 |
| num_turns | 9 / 9 | 8 / 8 | +1 | +1 |
| duration_ms | 33024 / 33024 | 21497 / 21497 | +11527 | +11527 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 1987 / 1987 | 1782 / 1782 | +205 | +205 |
| cache_creation_input_tokens | 39196 / 39196 | 14136 / 14136 | +25060 | +25060 |
| cache_read_input_tokens | 293590 / 293590 | 243300 / 243300 | +50290 | +50290 |
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
