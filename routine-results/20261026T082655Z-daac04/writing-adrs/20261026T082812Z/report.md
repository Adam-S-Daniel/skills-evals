# Eval report: writing-adrs

- Timestamp: 20261026T082812Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T082655Z-daac04; started 2026-10-26T08:28:12Z, ended 2026-10-26T08:33:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.02, seven_day 0.57 to 0.57, from 6 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.3579 / 1.0737 |
| without_skill | 3 | 0 | 3/9 | skipped (objective-decided) | 0.2958 / 0.8873 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3579 / 0.3508 | 0.2958 / 0.2960 | +0.0621 | +0.0549 |
| num_turns | 7.7 / 7 | 6.3 / 6 | +1.3 | +1 |
| duration_ms | 51376 / 53428 | 44211 / 44913 | +7165 | +8515 |
| input_tokens | 12.7 / 12 | 11.3 / 12 | +1.3 | 0 |
| output_tokens | 3893.7 / 3691 | 3352.7 / 3417 | +541 | +274 |
| cache_creation_input_tokens | 29532 / 29450 | 24078.3 / 23885 | +5453.7 | +5565 |
| cache_read_input_tokens | 218628 / 206909 | 180157.7 / 192278 | +38470.3 | +14631 |
| tool_errors | 1 / 1 | 0.7 / 1 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 0/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
