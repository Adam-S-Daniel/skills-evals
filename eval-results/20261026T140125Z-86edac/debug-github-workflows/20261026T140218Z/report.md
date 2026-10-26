# Eval report: debug-github-workflows

- Timestamp: 20261026T140218Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140125Z-86edac; started 2026-10-26T14:02:18Z, ended 2026-10-26T14:08:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.23 to 0.29, seven_day 0.7 to 0.71, from 10 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | 8.9 (8.8 to 9.0, 3 judged) | 0.1796 / 0.5389 |
| without_skill | 3 | 0 | 5.7/7 | 8.9 (8.8 to 9.0, 3 judged) | 0.1915 / 0.5746 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1796 / 0.1717 | 0.1915 / 0.1786 | -0.0119 | -0.0069 |
| num_turns | 5.3 / 5 | 5.7 / 5 | -0.3 | 0 |
| duration_ms | 31794 / 30175 | 38143.3 / 30114 | -6349.3 | +61 |
| input_tokens | 10.7 / 10 | 11.3 / 10 | -0.7 | 0 |
| output_tokens | 1972.3 / 1953 | 2116.3 / 1982 | -144 | -29 |
| cache_creation_input_tokens | 12681.3 / 12137 | 13416.7 / 12850 | -735.3 | -713 |
| cache_read_input_tokens | 192773.3 / 178281 | 208564.3 / 180124 | -15791 | -1843 |
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
