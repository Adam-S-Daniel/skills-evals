# Eval report: debug-github-workflows

- Timestamp: 20261103T064838Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T064657Z-265488; started 2026-11-03T06:48:38Z, ended 2026-11-03T06:50:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.21, judge $0.16, guard $0.00; last agent call $0.07

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1327 / 0.1327 |
| without_skill | 1 | 0 | 6/7 | 7.4 (7.4 to 7.4, 1 judged) | 0.0746 / 0.0746 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1327 / 0.1327 | 0.0746 / 0.0746 | +0.0580 | +0.0580 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 23529 / 23529 | 24169 / 24169 | -640 | -640 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1661 / 1661 | 1303 / 1303 | +358 | +358 |
| cache_creation_input_tokens | 25026 / 25026 | 12116 / 12116 | +12910 | +12910 |
| cache_read_input_tokens | 159360 / 159360 | 131115 / 131115 | +28245 | +28245 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
