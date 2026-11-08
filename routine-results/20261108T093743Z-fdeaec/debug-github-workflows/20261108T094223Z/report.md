# Eval report: debug-github-workflows

- Timestamp: 20261108T094223Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T093743Z-fdeaec; started 2026-11-08T09:42:23Z, ended 2026-11-08T09:43:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 7.8 (7.8 to 7.8, 1 judged) | 0.1301 / 0.1301 |
| without_skill | 1 | 0 | 7/7 | 5.6 (5.6 to 5.6, 1 judged) | 0.0865 / 0.0865 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1301 / 0.1301 | 0.0865 / 0.0865 | +0.0436 | +0.0436 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 20437 / 20437 | 22689 / 22689 | -2252 | -2252 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1663 / 1663 | 1545 / 1545 | +118 | +118 |
| cache_creation_input_tokens | 23525 / 23525 | 13575 / 13575 | +9950 | +9950 |
| cache_read_input_tokens | 193097 / 193097 | 166863 / 166863 | +26234 | +26234 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
