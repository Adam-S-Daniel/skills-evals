# Eval report: debug-github-workflows

- Timestamp: 20261109T203220Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T203013Z-063d90; started 2026-11-09T20:32:20Z, ended 2026-11-09T20:33:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.09 to 0.09, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.65 over 4 call(s); agent $0.48, judge $0.17, guard $0.00; last agent call $0.19

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.2916 / 0.2916 |
| without_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1873 / 0.1873 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2916 / 0.2916 | 0.1873 / 0.1873 | +0.1042 | +0.1042 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 30954 / 30954 | 31327 / 31327 | -373 | -373 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2506 / 2506 | 2718 / 2718 | -212 | -212 |
| cache_creation_input_tokens | 40827 / 40827 | 17958 / 17958 | +22869 | +22869 |
| cache_read_input_tokens | 186330 / 186330 | 215747 / 215747 | -29417 | -29417 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
