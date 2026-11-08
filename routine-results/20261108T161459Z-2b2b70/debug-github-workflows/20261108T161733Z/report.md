# Eval report: debug-github-workflows

- Timestamp: 20261108T161733Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T161459Z-2b2b70; started 2026-11-08T16:17:33Z, ended 2026-11-08T16:19:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 4 call(s); agent $0.50, judge $0.23, guard $0.00; last agent call $0.19

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.3145 / 0.3145 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1854 / 0.1854 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3145 / 0.3145 | 0.1854 / 0.1854 | +0.1291 | +0.1291 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 44880 / 44880 | 43586 / 43586 | +1294 | +1294 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 2810 / 2810 | 2594 / 2594 | +216 | +216 |
| cache_creation_input_tokens | 43731 / 43731 | 16632 / 16632 | +27099 | +27099 |
| cache_read_input_tokens | 197964 / 197964 | 251596 / 251596 | -53632 | -53632 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
