# Eval report: workflow-path-audit

- Timestamp: 20261108T044811Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T044626Z-9a7707; started 2026-11-08T04:48:11Z, ended 2026-11-08T04:52:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.19 over 2 call(s); agent $1.19, judge $0.00, guard $0.00; last agent call $0.72

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.4682 / 0.4682 |
| without_skill | 1 | 0 | 4/8 | skipped (objective-decided) | 0.7184 / 0.7184 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4682 / 0.4682 | 0.7184 / 0.7184 | -0.2502 | -0.2502 |
| num_turns | 9 / 9 | 11 / 11 | -2 | -2 |
| duration_ms | 88841 / 88841 | 156602 / 156602 | -67761 | -67761 |
| input_tokens | 20 / 20 | 24 / 24 | -4 | -4 |
| output_tokens | 5826 / 5826 | 11276 / 11276 | -5450 | -5450 |
| cache_creation_input_tokens | 35197 / 35197 | 31968 / 31968 | +3229 | +3229 |
| cache_read_input_tokens | 319677 / 319677 | 472733 / 472733 | -153056 | -153056 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 1/1 |
| docs-change-still-reports-the-required-check | 1/1 | 1/1 |
| source-change-skips-the-docs-site | 1/1 | 0/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 0/1 |
| project-files-unchanged | 1/1 | 0/1 |
