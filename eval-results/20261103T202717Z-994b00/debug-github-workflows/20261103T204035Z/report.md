# Eval report: debug-github-workflows

- Timestamp: 20261103T204035Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T202717Z-994b00; started 2026-11-03T20:40:35Z, ended 2026-11-03T20:42:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 2 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3175 / 0.3175 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.2299 / 0.2299 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3175 / 0.3175 | 0.2299 / 0.2299 | +0.0876 | +0.0876 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 30743 / 30743 | 50856 / 50856 | -20113 | -20113 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2815 / 2815 | 2605 / 2605 | +210 | +210 |
| cache_creation_input_tokens | 27538 / 27538 | 16842 / 16842 | +10696 | +10696 |
| cache_read_input_tokens | 204209 / 204209 | 214958 / 214958 | -10749 | -10749 |
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
