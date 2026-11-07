# Eval report: workflow-path-audit

- Timestamp: 20261107T122808Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T122635Z-90ba7c; started 2026-11-07T12:28:08Z, ended 2026-11-07T12:29:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.43, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: companion-skip-pair (n=2)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 8/8 | skipped (objective-decided) | 0.1345 / 0.2690 |
| without_skill | 2 | 0 | 5/8 | skipped (objective-decided) | 0.0826 / 0.1652 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1345 / 0.1345 | 0.0826 / 0.0826 | +0.0519 | +0.0519 |
| num_turns | 6 / 6 | 4.5 / 4.5 | +1.5 | +1.5 |
| duration_ms | 31451.5 / 31451.5 | 20021.5 / 20021.5 | +11430 | +11430 |
| input_tokens | 11 / 11 | 9 / 9 | +2 | +2 |
| output_tokens | 2815.5 / 2815.5 | 1573.5 / 1573.5 | +1242 | +1242 |
| cache_creation_input_tokens | 22295 / 22295 | 12954.5 / 12954.5 | +9340.5 | +9340.5 |
| cache_read_input_tokens | 171448.5 / 171448.5 | 150153.5 / 150153.5 | +21295 | +21295 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 2/2 | 0/2 |
| companion-skip-workflow-removed | 2/2 | 0/2 |
| docs-change-still-reports-the-required-check | 2/2 | 0/2 |
| source-change-skips-the-docs-site | 2/2 | 2/2 |
| workflows-still-parse | 2/2 | 2/2 |
| event-only-workflows-unfiltered | 2/2 | 2/2 |
| ruleset-unchanged | 2/2 | 2/2 |
| project-files-unchanged | 2/2 | 2/2 |
