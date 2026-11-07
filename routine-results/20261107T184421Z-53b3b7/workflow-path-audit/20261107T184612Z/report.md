# Eval report: workflow-path-audit

- Timestamp: 20261107T184612Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184421Z-53b3b7; started 2026-11-07T18:46:12Z, ended 2026-11-07T18:58:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.62, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.27 over 6 call(s); agent $3.27, judge $0.00, guard $0.00; last agent call $0.58

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.4505 / 1.3514 |
| without_skill | 3 | 0 | 6/8 | skipped (objective-decided) | 0.6380 / 1.9140 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4505 / 0.4073 | 0.6380 / 0.6627 | -0.1875 | -0.2554 |
| num_turns | 10 / 11 | 10.7 / 11 | -0.7 | 0 |
| duration_ms | 88345.7 / 87862 | 149718 / 134922 | -61372.3 | -47060 |
| input_tokens | 22 / 24 | 23.3 / 24 | -1.3 | 0 |
| output_tokens | 5802.7 / 5400 | 10521.3 / 9785 | -4718.7 | -4385 |
| cache_creation_input_tokens | 31532 / 27734 | 32052.7 / 31742 | -520.7 | -4008 |
| cache_read_input_tokens | 383970.3 / 430610 | 466600.7 / 461981 | -82630.3 | -31371 |
| tool_errors | 0 / 0 | 3 / 2 | -3 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 3/3 | 1/3 |
| companion-skip-workflow-removed | 3/3 | 1/3 |
| docs-change-still-reports-the-required-check | 3/3 | 1/3 |
| source-change-skips-the-docs-site | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
