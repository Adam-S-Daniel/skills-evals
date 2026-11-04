# Eval report: workflow-path-audit

- Timestamp: 20261104T184148Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T184005Z-14cb0e; started 2026-11-04T18:41:48Z, ended 2026-11-04T18:42:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1534 / 0.1534 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0926 / 0.0926 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1534 / 0.1534 | 0.0926 / 0.0926 | +0.0607 | +0.0607 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 28856 / 28856 | 37092 / 37092 | -8236 | -8236 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2143 / 2143 | 2034 / 2034 | +109 | +109 |
| cache_creation_input_tokens | 28691 / 28691 | 14673 / 14673 | +14018 | +14018 |
| cache_read_input_tokens | 171450 / 171450 | 135800 / 135800 | +35650 | +35650 |
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
