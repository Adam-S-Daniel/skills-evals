# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T192846Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192714Z-be1f65; started 2026-11-07T19:28:46Z, ended 2026-11-07T19:36:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.15 over 6 call(s); agent $2.15, judge $0.00, guard $0.00; last agent call $0.32

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2/3 | skipped (objective-decided) | 0.3833 / 1.1498 |
| without_skill | 3 | 0 | 1.7/3 | skipped (objective-decided) | 0.3334 / 1.0003 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3833 / 0.3810 | 0.3334 / 0.3170 | +0.0498 | +0.0640 |
| num_turns | 7 / 7 | 6.7 / 7 | +0.3 | 0 |
| duration_ms | 72856.3 / 83389 | 83388.7 / 90304 | -10532.3 | -6915 |
| input_tokens | 14.7 / 14 | 15.3 / 16 | -0.7 | -2 |
| output_tokens | 5266.3 / 5261 | 4429.7 / 4506 | +836.7 | +755 |
| cache_creation_input_tokens | 23445 / 22698 | 19447 / 19836 | +3998 | +2862 |
| cache_read_input_tokens | 249400.3 / 221770 | 248401.3 / 260811 | +999 | -39041 |
| tool_errors | 1 / 1 | 1.7 / 2 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 3/3 | 3/3 |
| still-gated | 0/3 | 0/3 |
| site-untouched | 3/3 | 2/3 |
