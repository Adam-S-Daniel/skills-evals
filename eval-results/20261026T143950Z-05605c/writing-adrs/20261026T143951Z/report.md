# Eval report: writing-adrs

- Timestamp: 20261026T143951Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143950Z-05605c; started 2026-10-26T14:39:51Z, ended 2026-10-26T14:45:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.54 to 0.56, seven_day 0.77 to 0.78, from 8 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.8 (9.5 to 10.0, 3 judged) | 0.2030 / 0.6089 |
| without_skill | 3 | 0 | 7/7 | 9.4 (9.1 to 9.5, 3 judged) | 0.1847 / 0.5540 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2030 / 0.2014 | 0.1847 / 0.1752 | +0.0183 | +0.0262 |
| num_turns | 6 / 6 | 4.7 / 4 | +1.3 | +2 |
| duration_ms | 32645 / 33601 | 32183.7 / 30547 | +461.3 | +3054 |
| input_tokens | 6.7 / 6 | 9.3 / 8 | -2.7 | -2 |
| output_tokens | 2328 / 2456 | 2247.7 / 2007 | +80.3 | +449 |
| cache_creation_input_tokens | 16525.7 / 16370 | 13270.7 / 13353 | +3255 | +3017 |
| cache_read_input_tokens | 120161.3 / 105672 | 166916 / 140153 | -46754.7 | -34481 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
