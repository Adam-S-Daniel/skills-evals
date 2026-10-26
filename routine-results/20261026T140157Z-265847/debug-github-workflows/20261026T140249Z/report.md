# Eval report: debug-github-workflows

- Timestamp: 20261026T140249Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140157Z-265847; started 2026-10-26T14:02:49Z, ended 2026-10-26T14:06:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.25 to 0.27, seven_day 0.71 to 0.71, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 7.2 (4.8 to 8.8, 3 judged) | 0.0890 / 0.2670 |
| without_skill | 3 | 0 | 6.3/7 | 9.0 (8.8 to 9.2, 3 judged) | 0.0784 / 0.2353 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0890 / 0.0945 | 0.0784 / 0.0818 | +0.0106 | +0.0127 |
| num_turns | 7.7 / 8 | 6 / 6 | +1.7 | +2 |
| duration_ms | 18238.7 / 19928 | 17057 / 17179 | +1181.7 | +2749 |
| input_tokens | 11.3 / 12 | 10.7 / 10 | +0.7 | +2 |
| output_tokens | 1518.7 / 1655 | 1409.3 / 1502 | +109.3 | +153 |
| cache_creation_input_tokens | 13191.3 / 13676 | 11287.3 / 11278 | +1904 | +2398 |
| cache_read_input_tokens | 208826 / 222140 | 190304 / 178834 | +18522 | +43306 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 2/3 |
| feature-comparison-read | 1/3 | 2/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
