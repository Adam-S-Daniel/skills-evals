# Eval report: writing-adrs

- Timestamp: 20261025T232304Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T232217Z-6836ce; started 2026-10-25T23:23:04Z, ended 2026-10-25T23:28:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.07 to 0.08, seven_day 0.49 to 0.49, from 6 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 10.0 (10.0 to 10.0, 3 judged) | 0.3017 / 0.9052 |
| without_skill | 3 | 0 | 7/7 | 9.3 (9.0 to 9.5, 3 judged) | 0.1798 / 0.5393 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3017 / 0.2499 | 0.1798 / 0.1783 | +0.1220 | +0.0716 |
| num_turns | 7 / 8 | 5 / 5 | +2 | +3 |
| duration_ms | 35375.3 / 39326 | 33030.7 / 28460 | +2344.7 | +10866 |
| input_tokens | 9.3 / 10 | 9.3 / 10 | 0 | 0 |
| output_tokens | 2682.3 / 2955 | 2085.3 / 1955 | +597 | +1000 |
| cache_creation_input_tokens | 26739.7 / 17834 | 13039.7 / 12987 | +13700 | +4847 |
| cache_read_input_tokens | 170090 / 164514 | 167887.7 / 180705 | +2202.3 | -16191 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
