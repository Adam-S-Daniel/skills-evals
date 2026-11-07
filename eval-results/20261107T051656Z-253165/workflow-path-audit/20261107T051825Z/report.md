# Eval report: workflow-path-audit

- Timestamp: 20261107T051825Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051656Z-253165; started 2026-11-07T05:18:25Z, ended 2026-11-07T05:19:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1583 / 0.1583 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.1407 / 0.1407 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1583 / 0.1583 | 0.1407 / 0.1407 | +0.0176 | +0.0176 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 22801 / 22801 | 47533 / 47533 | -24732 | -24732 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2168 / 2168 | 4911 / 4911 | -2743 | -2743 |
| cache_creation_input_tokens | 28820 / 28820 | 16708 / 16708 | +12112 | +12112 |
| cache_read_input_tokens | 213393 / 213393 | 247347 / 247347 | -33954 | -33954 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 1/1 |
| docs-change-still-reports-the-required-check | 1/1 | 1/1 |
| source-change-skips-the-docs-site | 1/1 | 0/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 0/1 |
| project-files-unchanged | 1/1 | 1/1 |
