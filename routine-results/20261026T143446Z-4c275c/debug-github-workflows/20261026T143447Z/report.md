# Eval report: debug-github-workflows

- Timestamp: 20261026T143447Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143446Z-4c275c; started 2026-10-26T14:34:47Z, ended 2026-10-26T14:38:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.5 to 0.53, seven_day 0.76 to 0.77, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.1875 / 0.5625 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.1909 / 0.5728 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1875 / 0.1885 | 0.1909 / 0.1941 | -0.0034 | -0.0056 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 33329 / 34587 | 35631.3 / 36154 | -2302.3 | -1567 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 1813 / 1890 | 2159 / 2213 | -346 | -323 |
| cache_creation_input_tokens | 13354 / 13233 | 12962.3 / 13061 | +391.7 | +172 |
| cache_read_input_tokens | 221125.7 / 218348 | 219382.3 / 220001 | +1743.3 | -1653 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 1/3 |
| feature-comparison-read | 1/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
