# Eval report: debug-github-workflows

- Timestamp: 20261026T145847Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T145751Z-20b35b; started 2026-10-26T14:58:47Z, ended 2026-10-26T15:03:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.7 to 0.72, seven_day 0.8 to 0.81, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 8.8 (8.8 to 8.8, 3 judged) | 0.0896 / 0.2689 |
| without_skill | 3 | 0 | 5.3/7 | 7.1 (4.8 to 8.8, 3 judged) | 0.0758 / 0.2274 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0896 / 0.0880 | 0.0758 / 0.0780 | +0.0138 | +0.0100 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 28254.7 / 28509 | 28188.7 / 23575 | +66 | +4934 |
| input_tokens | 11.3 / 10 | 10.7 / 12 | +0.7 | -2 |
| output_tokens | 1587.7 / 1718 | 1196 / 1280 | +391.7 | +438 |
| cache_creation_input_tokens | 13187.3 / 13050 | 11159.7 / 10852 | +2027.7 | +2198 |
| cache_read_input_tokens | 208592.3 / 182790 | 190388 / 214728 | +18204.3 | -31938 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 2/3 |
| feature-comparison-read | 0/3 | 1/3 |
| main-differs-from-feature | 3/3 | 2/3 |
| merge-existing-fix | 3/3 | 2/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
