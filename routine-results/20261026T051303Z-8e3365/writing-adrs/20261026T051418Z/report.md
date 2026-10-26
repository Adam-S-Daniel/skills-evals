# Eval report: writing-adrs

- Timestamp: 20261026T051418Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T051303Z-8e3365; started 2026-10-26T05:14:18Z, ended 2026-10-26T05:20:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.1, seven_day 0.55 to 0.55, from 8 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.7/9 | skipped (objective-decided) | 0.3882 / 1.1645 |
| without_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.3092 / 0.9276 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3882 / 0.3899 | 0.3092 / 0.3035 | +0.0790 | +0.0864 |
| num_turns | 10.3 / 11 | 6.7 / 6 | +3.7 | +5 |
| duration_ms | 63349.7 / 63109 | 49054.3 / 51217 | +14295.3 | +11892 |
| input_tokens | 18 / 20 | 13.3 / 12 | +4.7 | +8 |
| output_tokens | 4219.3 / 4004 | 3421.3 / 3387 | +798 | +617 |
| cache_creation_input_tokens | 29741.7 / 29519 | 24631.7 / 24644 | +5110 | +4875 |
| cache_read_input_tokens | 328898 / 367715 | 218319.7 / 192595 | +110578.3 | +175120 |
| tool_errors | 1.7 / 2 | 1.3 / 1 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 1/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 2/3 | 0/3 |
