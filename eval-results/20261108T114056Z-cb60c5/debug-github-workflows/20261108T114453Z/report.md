# Eval report: debug-github-workflows

- Timestamp: 20261108T114453Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T114056Z-cb60c5; started 2026-11-08T11:44:53Z, ended 2026-11-08T11:46:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/7 | 3.6 (3.6 to 3.6, 1 judged) | 0.1325 / 0.1325 |
| without_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.0833 / 0.0833 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1325 / 0.1325 | 0.0833 / 0.0833 | +0.0492 | +0.0492 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 33713 / 33713 | 26494 / 26494 | +7219 | +7219 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 1724 / 1724 | 1329 / 1329 | +395 | +395 |
| cache_creation_input_tokens | 23086 / 23086 | 13301 / 13301 | +9785 | +9785 |
| cache_read_input_tokens | 229291 / 229291 | 167823 / 167823 | +61468 | +61468 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 0/1 | 1/1 |
| merge-existing-fix | 0/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
