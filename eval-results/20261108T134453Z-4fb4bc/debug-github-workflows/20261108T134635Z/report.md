# Eval report: debug-github-workflows

- Timestamp: 20261108T134635Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T134453Z-4fb4bc; started 2026-11-08T13:46:35Z, ended 2026-11-08T13:48:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.77, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 4 call(s); agent $0.54, judge $0.29, guard $0.00; last agent call $0.25

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.2903 / 0.2903 |
| without_skill | 1 | 0 | 7/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.2507 / 0.2507 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2903 / 0.2903 | 0.2507 / 0.2507 | +0.0396 | +0.0396 |
| num_turns | 5 / 5 | 8 / 8 | -3 | -3 |
| duration_ms | 33154 / 33154 | 48766 / 48766 | -15612 | -15612 |
| input_tokens | 10 / 10 | 16 / 16 | -6 | -6 |
| output_tokens | 2671 / 2671 | 2801 / 2801 | -130 | -130 |
| cache_creation_input_tokens | 25581 / 25581 | 16987 / 16987 | +8594 | +8594 |
| cache_read_input_tokens | 161011 / 161011 | 293517 / 293517 | -132506 | -132506 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
