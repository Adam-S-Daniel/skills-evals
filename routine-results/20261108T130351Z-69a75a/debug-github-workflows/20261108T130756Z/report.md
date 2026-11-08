# Eval report: debug-github-workflows

- Timestamp: 20261108T130756Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T130351Z-69a75a; started 2026-11-08T13:07:56Z, ended 2026-11-08T13:09:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.21, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1314 / 0.1314 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0800 / 0.0800 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1314 / 0.1314 | 0.0800 / 0.0800 | +0.0513 | +0.0513 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 25990 / 25990 | 26773 / 26773 | -783 | -783 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1569 / 1569 | 1304 / 1304 | +265 | +265 |
| cache_creation_input_tokens | 24025 / 24025 | 12558 / 12558 | +11467 | +11467 |
| cache_read_input_tokens | 195791 / 195791 | 167579 / 167579 | +28212 | +28212 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
