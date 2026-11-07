# Eval report: debug-github-workflows

- Timestamp: 20261107T045615Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T045441Z-65c04a; started 2026-11-07T04:56:15Z, ended 2026-11-07T04:56:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 2 call(s); agent $0.21, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1296 / 0.1296 |
| without_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.0790 / 0.0790 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1296 / 0.1296 | 0.0790 / 0.0790 | +0.0506 | +0.0506 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 22754 / 22754 | 15953 / 15953 | +6801 | +6801 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1563 / 1563 | 1234 / 1234 | +329 | +329 |
| cache_creation_input_tokens | 23626 / 23626 | 12476 / 12476 | +11150 | +11150 |
| cache_read_input_tokens | 194126 / 194126 | 167549 / 167549 | +26577 | +26577 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 0/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
