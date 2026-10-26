# Eval report: debug-github-workflows

- Timestamp: 20261026T123223Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T123129Z-58e10f; started 2026-10-26T12:32:23Z, ended 2026-10-26T12:37:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.34 to 0.35, seven_day 0.64 to 0.65, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 8.8 (8.8 to 8.8, 3 judged) | 0.0819 / 0.2457 |
| without_skill | 3 | 0 | 5.3/7 | 7.1 (4.2 to 8.8, 3 judged) | 0.0743 / 0.2230 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0819 / 0.0819 | 0.0743 / 0.0710 | +0.0076 | +0.0109 |
| num_turns | 7 / 7 | 5.7 / 5 | +1.3 | +2 |
| duration_ms | 27951.7 / 25494 | 41802.7 / 31542 | -13851 | -6048 |
| input_tokens | 10 / 10 | 10.7 / 10 | -0.7 | 0 |
| output_tokens | 1338 / 1302 | 1240.7 / 1215 | +97.3 | +87 |
| cache_creation_input_tokens | 12562.3 / 12629 | 10717.7 / 10294 | +1844.7 | +2335 |
| cache_read_input_tokens | 181382 / 182045 | 188925 / 176285 | -7543 | +5760 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 1/3 |
| feature-comparison-read | 0/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
