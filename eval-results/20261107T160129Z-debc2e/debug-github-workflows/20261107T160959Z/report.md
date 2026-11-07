# Eval report: debug-github-workflows

- Timestamp: 20261107T160959Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T160129Z-debc2e; started 2026-11-07T16:09:59Z, ended 2026-11-07T16:12:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.53, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 6 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.0958 / 0.2875 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.0884 / 0.2653 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0958 / 0.0858 | 0.0884 / 0.0906 | +0.0074 | -0.0048 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 18828 / 19705 | 23397.3 / 22177 | -4569.3 | -2472 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1382 / 1413 | 1609 / 1618 | -227 | -205 |
| cache_creation_input_tokens | 16407 / 13640 | 13268.7 / 13456 | +3138.3 | +184 |
| cache_read_input_tokens | 163633.7 / 166801 | 192568.3 / 205480 | -28934.7 | -38679 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 2/3 | 1/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
