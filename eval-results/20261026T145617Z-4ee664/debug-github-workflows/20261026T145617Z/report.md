# Eval report: debug-github-workflows

- Timestamp: 20261026T145617Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145617Z-4ee664; started 2026-10-26T14:56:17Z, ended 2026-10-26T14:59:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.68 to 0.71, seven_day 0.8 to 0.81, from 9 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.1848 / 0.5544 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1752 / 0.5256 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1848 / 0.1918 | 0.1752 / 0.1762 | +0.0096 | +0.0156 |
| num_turns | 5.7 / 5 | 5 / 5 | +0.7 | 0 |
| duration_ms | 35420 / 32999 | 27996.3 / 28215 | +7423.7 | +4784 |
| input_tokens | 11.3 / 10 | 10 / 10 | +1.3 | 0 |
| output_tokens | 2042.7 / 2241 | 1885 / 2015 | +157.7 | +226 |
| cache_creation_input_tokens | 12856.7 / 12805 | 12687.7 / 12743 | +169 | +62 |
| cache_read_input_tokens | 204587.7 / 180657 | 179233.3 / 179199 | +25354.3 | +1458 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 1/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
