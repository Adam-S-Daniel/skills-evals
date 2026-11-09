# Eval report: debug-github-workflows

- Timestamp: 20261109T213839Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T213621Z-08aa9a; started 2026-11-09T21:38:39Z, ended 2026-11-09T21:40:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 4 call(s); agent $0.48, judge $0.17, guard $0.00; last agent call $0.20

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.2852 / 0.2852 |
| without_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1993 / 0.1993 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2852 / 0.2852 | 0.1993 / 0.1993 | +0.0859 | +0.0859 |
| num_turns | 6 / 6 | 8 / 8 | -2 | -2 |
| duration_ms | 27123 / 27123 | 34914 / 34914 | -7791 | -7791 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 2318 / 2318 | 3107 / 3107 | -789 | -789 |
| cache_creation_input_tokens | 40335 / 40335 | 17261 / 17261 | +23074 | +23074 |
| cache_read_input_tokens | 185669 / 185669 | 253848 / 253848 | -68179 | -68179 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
