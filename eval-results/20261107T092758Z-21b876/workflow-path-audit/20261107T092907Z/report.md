# Eval report: workflow-path-audit

- Timestamp: 20261107T092907Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T092758Z-21b876; started 2026-11-07T09:29:07Z, ended 2026-11-07T09:30:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 6 call(s); agent $0.22, judge $0.09, guard $0.00; last agent call $0.07

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/8 | 1.7 (1.4 to 1.8, 3 judged) | 0.0721 / 0.2162 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0721 / 0.0707 |
| num_turns | 4 / 4 |
| duration_ms | 28279.7 / 29392 |
| input_tokens | 8 / 8 |
| output_tokens | 1430.7 / 1324 |
| cache_creation_input_tokens | 10938.3 / 10866 |
| cache_read_input_tokens | 140035 / 140175 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| required-check-gates-inside-one-workflow | 0/3 |
| companion-skip-workflow-removed | 0/3 |
| docs-change-still-reports-the-required-check | 0/3 |
| source-change-skips-the-docs-site | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| ruleset-unchanged | 3/3 |
| project-files-unchanged | 3/3 |
