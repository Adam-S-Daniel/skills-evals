# Eval report: debug-github-workflows

- Timestamp: 20261103T203711Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T201648Z-ce45ac; started 2026-11-03T20:37:11Z, ended 2026-11-03T20:38:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.21, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/7 | 4.2 (4.2 to 4.2, 1 judged) | 0.1184 / 0.1184 |
| without_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.0886 / 0.0886 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1184 / 0.1184 | 0.0886 / 0.0886 | +0.0297 | +0.0297 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 14231 / 14231 | 26291 / 26291 | -12060 | -12060 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1300 / 1300 | 1607 / 1607 | -307 | -307 |
| cache_creation_input_tokens | 22425 / 22425 | 13923 / 13923 | +8502 | +8502 |
| cache_read_input_tokens | 156456 / 156456 | 168576 / 168576 | -12120 | -12120 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 0/1 | 1/1 |
| merge-existing-fix | 0/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
