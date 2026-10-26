# Eval report: writing-adrs

- Timestamp: 20261026T134230Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T134134Z-0019c7; started 2026-10-26T13:42:30Z, ended 2026-10-26T13:45:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.68 to 0.68, from 7 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | 10.0 (10.0 to 10.0, 3 judged) | 0.1817 / 0.5452 |
| without_skill | 3 | 0 | 11/11 | 10.0 (10.0 to 10.0, 3 judged) | 0.1503 / 0.4510 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1817 / 0.1770 | 0.1503 / 0.1502 | +0.0314 | +0.0267 |
| num_turns | 6.7 / 7 | 3.7 / 3 | +3 | +4 |
| duration_ms | 20338 / 18922 | 19160.3 / 19087 | +1177.7 | -165 |
| input_tokens | 6.7 / 6 | 6.7 / 6 | 0 | 0 |
| output_tokens | 1655.3 / 1676 | 1486 / 1522 | +169.3 | +154 |
| cache_creation_input_tokens | 15558.7 / 15644 | 12177.3 / 12093 | +3381.3 | +3551 |
| cache_read_input_tokens | 119929.7 / 106182 | 115157.7 / 102839 | +4772 | +3343 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
| nothing-else-touched | 3/3 | 3/3 |
