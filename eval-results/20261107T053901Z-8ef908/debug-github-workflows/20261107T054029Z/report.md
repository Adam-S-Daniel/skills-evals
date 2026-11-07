# Eval report: debug-github-workflows

- Timestamp: 20261107T054029Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T053901Z-8ef908; started 2026-11-07T05:40:29Z, ended 2026-11-07T05:41:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.1319 / 0.1319 |
| without_skill | 1 | 0 | 5/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.0906 / 0.0906 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1319 / 0.1319 | 0.0906 / 0.0906 | +0.0413 | +0.0413 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 21510 / 21510 | 24778 / 24778 | -3268 | -3268 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1710 / 1710 | 1671 / 1671 | +39 | +39 |
| cache_creation_input_tokens | 24722 / 24722 | 14226 / 14226 | +10496 | +10496 |
| cache_read_input_tokens | 158581 / 158581 | 169601 / 169601 | -11020 | -11020 |
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
