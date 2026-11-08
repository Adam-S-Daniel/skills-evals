# Eval report: debug-github-workflows

- Timestamp: 20261108T122539Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T122227Z-62e249; started 2026-11-08T12:25:39Z, ended 2026-11-08T12:26:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.22, judge $0.10, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 4.8 (4.8 to 4.8, 1 judged) | 0.1326 / 0.1326 |
| without_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.0879 / 0.0879 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1326 / 0.1326 | 0.0879 / 0.0879 | +0.0447 | +0.0447 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 21713 / 21713 | 18740 / 18740 | +2973 | +2973 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1680 / 1680 | 1636 / 1636 | +44 | +44 |
| cache_creation_input_tokens | 25011 / 25011 | 13635 / 13635 | +11376 | +11376 |
| cache_read_input_tokens | 157338 / 157338 | 169470 / 169470 | -12132 | -12132 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
