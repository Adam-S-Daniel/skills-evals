# Eval report: debug-github-workflows

- Timestamp: 20261109T205741Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T205517Z-06f449; started 2026-11-09T20:57:41Z, ended 2026-11-09T20:58:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.09 to 0.09, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 2 call(s); agent $0.48, judge $0.00, guard $0.00; last agent call $0.17

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3148 / 0.3148 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1699 / 0.1699 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3148 / 0.3148 | 0.1699 / 0.1699 | +0.1449 | +0.1449 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 35262 / 35262 | 29166 / 29166 | +6096 | +6096 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3034 / 3034 | 2664 / 2664 | +370 | +370 |
| cache_creation_input_tokens | 41722 / 41722 | 16347 / 16347 | +25375 | +25375 |
| cache_read_input_tokens | 227141 / 227141 | 174114 / 174114 | +53027 | +53027 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
