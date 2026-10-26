# Eval report: writing-adrs

- Timestamp: 20261026T144225Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144224Z-f0b188; started 2026-10-26T14:42:25Z, ended 2026-10-26T14:48:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.55 to 0.58, seven_day 0.78 to 0.78, from 9 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.8 (9.5 to 10.0, 3 judged) | 0.2009 / 0.6027 |
| without_skill | 3 | 0 | 7/7 | 9.7 (9.5 to 10.0, 3 judged) | 0.1927 / 0.5782 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2009 / 0.1998 | 0.1927 / 0.2094 | +0.0082 | -0.0096 |
| num_turns | 6.3 / 7 | 5 / 6 | +1.3 | +1 |
| duration_ms | 33567 / 34597 | 35887.3 / 40810 | -2320.3 | -6213 |
| input_tokens | 8 / 8 | 10 / 12 | -2 | -4 |
| output_tokens | 2177 / 2174 | 2467.3 / 2757 | -290.3 | -583 |
| cache_creation_input_tokens | 15966.7 / 15862 | 13372.3 / 13739 | +2594.3 | +2123 |
| cache_read_input_tokens | 147283 / 146405 | 181193.3 / 220717 | -33910.3 | -74312 |
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
