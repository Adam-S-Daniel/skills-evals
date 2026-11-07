# Eval report: debug-github-workflows

- Timestamp: 20261107T080000Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T075834Z-a1d278; started 2026-11-07T08:00:00Z, ended 2026-11-07T08:00:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1249 / 0.1249 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.0772 / 0.0772 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1249 / 0.1249 | 0.0772 / 0.0772 | +0.0477 | +0.0477 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 21232 / 21232 | 16138 / 16138 | +5094 | +5094 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1395 / 1395 | 1334 / 1334 | +61 | +61 |
| cache_creation_input_tokens | 23793 / 23793 | 12684 / 12684 | +11109 | +11109 |
| cache_read_input_tokens | 157984 / 157984 | 131267 / 131267 | +26717 | +26717 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
