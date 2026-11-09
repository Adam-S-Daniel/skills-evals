# Eval report: debug-github-workflows

- Timestamp: 20261109T195227Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T195000Z-db158a; started 2026-11-09T19:52:27Z, ended 2026-11-09T19:53:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 2 call(s); agent $0.52, judge $0.00, guard $0.00; last agent call $0.20

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3194 / 0.3194 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.2024 / 0.2024 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3194 / 0.3194 | 0.2024 / 0.2024 | +0.1170 | +0.1170 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 36219 / 36219 | 38878 / 38878 | -2659 | -2659 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3128 / 3128 | 3066 / 3066 | +62 | +62 |
| cache_creation_input_tokens | 42161 / 42161 | 17939 / 17939 | +24222 | +24222 |
| cache_read_input_tokens | 229793 / 229793 | 256538 / 256538 | -26745 | -26745 |
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
