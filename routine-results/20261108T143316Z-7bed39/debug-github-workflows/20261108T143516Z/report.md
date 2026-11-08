# Eval report: debug-github-workflows

- Timestamp: 20261108T143516Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T143316Z-7bed39; started 2026-11-08T14:35:16Z, ended 2026-11-08T14:37:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 4 call(s); agent $0.56, judge $0.27, guard $0.00; last agent call $0.23

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.3253 / 0.3253 |
| without_skill | 1 | 0 | 5/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.2338 / 0.2338 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3253 / 0.3253 | 0.2338 / 0.2338 | +0.0916 | +0.0916 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 48934 / 48934 | 30095 / 30095 | +18839 | +18839 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2692 / 2692 | 2736 / 2736 | -44 | -44 |
| cache_creation_input_tokens | 28749 / 28749 | 17106 / 17106 | +11643 | +11643 |
| cache_read_input_tokens | 207335 / 207335 | 210879 / 210879 | -3544 | -3544 |
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
