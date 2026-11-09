# Eval report: debug-github-workflows

- Timestamp: 20261109T183959Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T183755Z-8b2048; started 2026-11-09T18:39:59Z, ended 2026-11-09T18:41:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 2 call(s); agent $0.52, judge $0.00, guard $0.00; last agent call $0.20

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3238 / 0.3238 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1991 / 0.1991 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3238 / 0.3238 | 0.1991 / 0.1991 | +0.1247 | +0.1247 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 38679 / 38679 | 35169 / 35169 | +3510 | +3510 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2926 / 2926 | 2931 / 2931 | -5 | -5 |
| cache_creation_input_tokens | 43733 / 43733 | 17941 / 17941 | +25792 | +25792 |
| cache_read_input_tokens | 232604 / 232604 | 253533 / 253533 | -20929 | -20929 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 1/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
