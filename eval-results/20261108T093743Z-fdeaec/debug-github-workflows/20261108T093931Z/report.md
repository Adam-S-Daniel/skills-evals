# Eval report: debug-github-workflows

- Timestamp: 20261108T093931Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T093743Z-fdeaec; started 2026-11-08T09:39:31Z, ended 2026-11-08T09:42:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.93 over 4 call(s); agent $0.62, judge $0.30, guard $0.00; last agent call $0.29

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.3355 / 0.3355 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.2892 / 0.2892 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3355 / 0.3355 | 0.2892 / 0.2892 | +0.0462 | +0.0462 |
| num_turns | 7 / 7 | 9 / 9 | -2 | -2 |
| duration_ms | 55778 / 55778 | 59349 / 59349 | -3571 | -3571 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 2878 / 2878 | 3303 / 3303 | -425 | -425 |
| cache_creation_input_tokens | 28608 / 28608 | 19296 / 19296 | +9312 | +9312 |
| cache_read_input_tokens | 244888 / 244888 | 343603 / 343603 | -98715 | -98715 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
