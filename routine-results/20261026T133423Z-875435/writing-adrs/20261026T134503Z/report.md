# Eval report: writing-adrs

- Timestamp: 20261026T134503Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133423Z-875435; started 2026-10-26T13:45:03Z, ended 2026-10-26T13:47:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.12 to 0.12, seven_day 0.68 to 0.68, from 6 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/11 | 9.0 (8.1 to 9.6, 3 judged) | 0.0919 / 0.2757 |
| without_skill | 3 | 0 | 10.3/11 | 9.7 (9.4 to 10.0, 3 judged) | 0.0787 / 0.2360 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0919 / 0.0918 | 0.0787 / 0.0774 | +0.0133 | +0.0144 |
| num_turns | 6 / 6 | 5 / 4 | +1 | +2 |
| duration_ms | 15299.7 / 14984 | 15471.7 / 15453 | -172 | -469 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 1556.3 / 1564 | 1630.7 / 1599 | -74.3 | -35 |
| cache_creation_input_tokens | 15369.3 / 15299 | 11729.3 / 11746 | +3640 | +3553 |
| cache_read_input_tokens | 147119.3 / 147092 | 152715.7 / 139794 | -5596.3 | +7298 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

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
| nothing-else-touched | 0/3 | 1/3 |
