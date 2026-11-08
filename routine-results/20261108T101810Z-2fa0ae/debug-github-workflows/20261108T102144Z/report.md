# Eval report: debug-github-workflows

- Timestamp: 20261108T102144Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T101810Z-2fa0ae; started 2026-11-08T10:21:44Z, ended 2026-11-08T10:22:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.21, judge $0.09, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1168 / 0.1168 |
| without_skill | 1 | 0 | 6/7 | 4.8 (4.8 to 4.8, 1 judged) | 0.0934 / 0.0934 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1168 / 0.1168 | 0.0934 / 0.0934 | +0.0234 | +0.0234 |
| num_turns | 4 / 4 | 7 / 7 | -3 | -3 |
| duration_ms | 16512 / 16512 | 25702 / 25702 | -9190 | -9190 |
| input_tokens | 8 / 8 | 14 / 14 | -6 | -6 |
| output_tokens | 1331 / 1331 | 1761 / 1761 | -430 | -430 |
| cache_creation_input_tokens | 22854 / 22854 | 13788 / 13788 | +9066 | +9066 |
| cache_read_input_tokens | 120511 / 120511 | 206218 / 206218 | -85707 | -85707 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
