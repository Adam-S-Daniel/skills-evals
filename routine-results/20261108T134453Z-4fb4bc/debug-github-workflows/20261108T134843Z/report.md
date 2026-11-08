# Eval report: debug-github-workflows

- Timestamp: 20261108T134843Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T134453Z-4fb4bc; started 2026-11-08T13:48:43Z, ended 2026-11-08T13:49:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.77 to 0.77, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.09, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1334 / 0.1334 |
| without_skill | 1 | 0 | 6/7 | 5.4 (5.4 to 5.4, 1 judged) | 0.0878 / 0.0878 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1334 / 0.1334 | 0.0878 / 0.0878 | +0.0456 | +0.0456 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 22920 / 22920 | 24735 / 24735 | -1815 | -1815 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 1596 / 1596 | 1684 / 1684 | -88 | -88 |
| cache_creation_input_tokens | 24434 / 24434 | 13525 / 13525 | +10909 | +10909 |
| cache_read_input_tokens | 196704 / 196704 | 168687 / 168687 | +28017 | +28017 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 0/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
