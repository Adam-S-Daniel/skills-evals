# Eval report: writing-adrs

- Timestamp: 20261026T112214Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T112114Z-c155dd; started 2026-10-26T11:22:14Z, ended 2026-10-26T11:25:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.17, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10.3/11 | 9.7 (9.4 to 10.0, 3 judged) | 0.0959 / 0.2876 |
| without_skill | 3 | 0 | 10.7/11 | 9.5 (9.4 to 9.5, 3 judged) | 0.0799 / 0.2396 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0959 / 0.0935 | 0.0799 / 0.0814 | +0.0160 | +0.0121 |
| num_turns | 7 / 6 | 6 / 7 | +1 | -1 |
| duration_ms | 24889.7 / 25988 | 19851 / 18774 | +5038.7 | +7214 |
| input_tokens | 8.7 / 8 | 9.3 / 10 | -0.7 | -2 |
| output_tokens | 1809.3 / 1719 | 1666.7 / 1728 | +142.7 | -9 |
| cache_creation_input_tokens | 15365 / 15366 | 11605.7 / 11598 | +3759.3 | +3768 |
| cache_read_input_tokens | 161381.3 / 147176 | 165686 / 178445 | -4304.7 | -31269 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| new-adr-0003-is-a-house-format-entry | 3/3 | 3/3 |
| adr-0003-records-the-reason | 3/3 | 3/3 |
| adr-0003-records-the-rejected-alternatives | 3/3 | 3/3 |
| index-gained-a-row-for-0003 | 3/3 | 3/3 |
| index-rows-for-0001-and-0002-kept | 3/3 | 3/3 |
| decision-log-links-resolve | 3/3 | 3/3 |
| script-comment-points-at-0003 | 3/3 | 3/3 |
| script-adr-pointers-resolve | 3/3 | 3/3 |
| script-still-writes-crlf | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 1/3 | 2/3 |
