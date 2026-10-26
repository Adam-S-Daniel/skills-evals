# Eval report: writing-adrs

- Timestamp: 20261026T135332Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135205Z-fa805f; started 2026-10-26T13:53:32Z, ended 2026-10-26T13:58:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.21, seven_day 0.69 to 0.7, from 10 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.3948 / 1.1844 |
| without_skill | 3 | 0 | 2.7/9 | skipped (objective-decided) | 0.3035 / 0.9105 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3948 / 0.3988 | 0.3035 / 0.3029 | +0.0913 | +0.0959 |
| num_turns | 10.3 / 9 | 7.7 / 8 | +2.7 | +1 |
| duration_ms | 58278.7 / 54057 | 43952.3 / 43658 | +14326.3 | +10399 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 4675.7 / 4831 | 3586.3 / 3528 | +1089.3 | +1303 |
| cache_creation_input_tokens | 30425.7 / 30460 | 24135.3 / 24218 | +6290.3 | +6242 |
| cache_read_input_tokens | 289134 / 289610 | 193236.3 / 193324 | +95897.7 | +96286 |
| tool_errors | 1.7 / 2 | 1.3 / 1 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 0/3 |
| nothing-else-touched | 3/3 | 2/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
