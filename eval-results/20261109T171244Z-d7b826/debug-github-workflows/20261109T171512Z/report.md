# Eval report: debug-github-workflows

- Timestamp: 20261109T171512Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T171244Z-d7b826; started 2026-11-09T17:15:12Z, ended 2026-11-09T17:18:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 4 call(s); agent $0.54, judge $0.37, guard $0.00; last agent call $0.24

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.2997 / 0.2997 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.2374 / 0.2374 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2997 / 0.2997 | 0.2374 / 0.2374 | +0.0622 | +0.0622 |
| num_turns | 9 / 9 | 10 / 10 | -1 | -1 |
| duration_ms | 50154 / 50154 | 45844 / 45844 | +4310 | +4310 |
| input_tokens | 18 / 18 | 20 / 20 | -2 | -2 |
| output_tokens | 4128 / 4128 | 3344 / 3344 | +784 | +784 |
| cache_creation_input_tokens | 30100 / 30100 | 19015 / 19015 | +11085 | +11085 |
| cache_read_input_tokens | 332611 / 332611 | 377010 / 377010 | -44399 | -44399 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
