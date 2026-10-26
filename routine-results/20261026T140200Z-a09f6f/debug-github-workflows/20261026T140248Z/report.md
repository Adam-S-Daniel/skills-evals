# Eval report: debug-github-workflows

- Timestamp: 20261026T140248Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140200Z-a09f6f; started 2026-10-26T14:02:48Z, ended 2026-10-26T14:09:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.24 to 0.29, seven_day 0.7 to 0.71, from 10 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | 9.0 (8.8 to 9.2, 3 judged) | 0.2173 / 0.6519 |
| without_skill | 3 | 0 | 5.7/7 | 8.8 (8.2 to 9.2, 3 judged) | 0.1929 / 0.5786 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2173 / 0.2209 | 0.1929 / 0.1967 | +0.0244 | +0.0243 |
| num_turns | 7.7 / 8 | 5.7 / 6 | +2 | +2 |
| duration_ms | 34599 / 36569 | 33009 / 32381 | +1590 | +4188 |
| input_tokens | 12.7 / 12 | 11.3 / 12 | +1.3 | 0 |
| output_tokens | 2167.7 / 2212 | 2211.7 / 2050 | -44 | +162 |
| cache_creation_input_tokens | 15736.7 / 15084 | 13364.7 / 13902 | +2372 | +1182 |
| cache_read_input_tokens | 239413 / 233487 | 207689.3 / 221308 | +31723.7 | +12179 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 1/3 |
| feature-comparison-read | 1/3 | 1/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
