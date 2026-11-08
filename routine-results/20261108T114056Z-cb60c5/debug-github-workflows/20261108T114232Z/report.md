# Eval report: debug-github-workflows

- Timestamp: 20261108T114232Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T114056Z-cb60c5; started 2026-11-08T11:42:32Z, ended 2026-11-08T11:44:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 4 call(s); agent $0.61, judge $0.29, guard $0.00; last agent call $0.26

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.3513 / 0.3513 |
| without_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.2600 / 0.2600 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3513 / 0.3513 | 0.2600 / 0.2600 | +0.0914 | +0.0914 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 50576 / 50576 | 36052 / 36052 | +14524 | +14524 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3568 / 3568 | 3260 / 3260 | +308 | +308 |
| cache_creation_input_tokens | 28854 / 28854 | 17968 / 17968 | +10886 | +10886 |
| cache_read_input_tokens | 245426 / 245426 | 254890 / 254890 | -9464 | -9464 |
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
