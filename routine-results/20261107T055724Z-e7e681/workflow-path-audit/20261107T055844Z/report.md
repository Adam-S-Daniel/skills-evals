# Eval report: workflow-path-audit

- Timestamp: 20261107T055844Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055724Z-e7e681; started 2026-11-07T05:58:44Z, ended 2026-11-07T05:59:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1582 / 0.1582 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.1044 / 0.1044 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1582 / 0.1582 | 0.1044 / 0.1044 | +0.0538 | +0.0538 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 22099 / 22099 | 30053 / 30053 | -7954 | -7954 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2435 / 2435 | 2561 / 2561 | -126 | -126 |
| cache_creation_input_tokens | 29150 / 29150 | 14481 / 14481 | +14669 | +14669 |
| cache_read_input_tokens | 172211 / 172211 | 207982 / 207982 | -35771 | -35771 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 0/1 |
| docs-change-still-reports-the-required-check | 1/1 | 0/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
