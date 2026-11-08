# Eval report: debug-github-workflows

- Timestamp: 20261108T122410Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T122227Z-62e249; started 2026-11-08T12:24:10Z, ended 2026-11-08T12:25:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 2 call(s); agent $0.56, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3353 / 0.3353 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2288 / 0.2288 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3353 / 0.3353 | 0.2288 / 0.2288 | +0.1065 | +0.1065 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 51066 / 51066 | 32965 / 32965 | +18101 | +18101 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3086 / 3086 | 2755 / 2755 | +331 | +331 |
| cache_creation_input_tokens | 28091 / 28091 | 15518 / 15518 | +12573 | +12573 |
| cache_read_input_tokens | 243797 / 243797 | 247539 / 247539 | -3742 | -3742 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 1/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
