# Eval report: debug-github-workflows

- Timestamp: 20261108T152231Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T152046Z-e0ae7f; started 2026-11-08T15:22:31Z, ended 2026-11-08T15:24:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 4 call(s); agent $0.50, judge $0.19, guard $0.00; last agent call $0.19

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.3143 / 0.3143 |
| without_skill | 1 | 0 | 5/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.1861 / 0.1861 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3143 / 0.3143 | 0.1861 / 0.1861 | +0.1282 | +0.1282 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 34314 / 34314 | 39518 / 39518 | -5204 | -5204 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2984 / 2984 | 3047 / 3047 | -63 | -63 |
| cache_creation_input_tokens | 43306 / 43306 | 16465 / 16465 | +26841 | +26841 |
| cache_read_input_tokens | 190081 / 190081 | 213871 / 213871 | -23790 | -23790 |
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
