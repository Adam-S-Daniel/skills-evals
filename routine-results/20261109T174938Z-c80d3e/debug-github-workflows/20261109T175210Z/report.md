# Eval report: debug-github-workflows

- Timestamp: 20261109T175210Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T174938Z-c80d3e; started 2026-11-09T17:52:10Z, ended 2026-11-09T17:54:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.02 to 0.03, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.77 over 4 call(s); agent $0.52, judge $0.24, guard $0.00; last agent call $0.21

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.3150 / 0.3150 |
| without_skill | 1 | 0 | 5/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.2084 / 0.2084 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3150 / 0.3150 | 0.2084 / 0.2084 | +0.1066 | +0.1066 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 32941 / 32941 | 35952 / 35952 | -3011 | -3011 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2569 / 2569 | 3193 / 3193 | -624 | -624 |
| cache_creation_input_tokens | 43311 / 43311 | 18593 / 18593 | +24718 | +24718 |
| cache_read_input_tokens | 235076 / 235076 | 257836 / 257836 | -22760 | -22760 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
