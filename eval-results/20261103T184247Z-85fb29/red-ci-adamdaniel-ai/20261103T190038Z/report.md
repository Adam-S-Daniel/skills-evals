# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T190038Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T184247Z-85fb29; started 2026-11-03T19:00:38Z, ended 2026-11-03T19:03:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.67, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 2 call(s); agent $0.89, judge $0.00, guard $0.00; last agent call $0.48

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.4166 / 0.4166 |
| without_skill | 1 | 0 | 1/3 | skipped (objective-decided) | 0.4766 / 0.4766 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4166 / 0.4166 | 0.4766 / 0.4766 | -0.0600 | -0.0600 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 77979 / 77979 | 76318 / 76318 | +1661 | +1661 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 5465 / 5465 | 5554 / 5554 | -89 | -89 |
| cache_creation_input_tokens | 31091 / 31091 | 21154 / 21154 | +9937 | +9937 |
| cache_read_input_tokens | 253635 / 253635 | 307721 / 307721 | -54086 | -54086 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 0/1 |
