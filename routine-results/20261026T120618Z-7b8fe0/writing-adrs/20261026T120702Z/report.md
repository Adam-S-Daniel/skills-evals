# Eval report: writing-adrs

- Timestamp: 20261026T120702Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T120618Z-7b8fe0; started 2026-10-26T12:07:02Z, ended 2026-10-26T12:10:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.22 to 0.23, seven_day 0.62 to 0.62, from 7 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10.3/11 | 8.7 (8.0 to 10.0, 3 judged) | 0.0935 / 0.2804 |
| without_skill | 3 | 0 | 11/11 | 9.8 (9.5 to 10.0, 3 judged) | 0.0803 / 0.2408 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0935 / 0.0915 | 0.0803 / 0.0829 | +0.0132 | +0.0086 |
| num_turns | 7 / 6 | 6 / 7 | +1 | -1 |
| duration_ms | 15870 / 15791 | 14885 / 15030 | +985 | +761 |
| input_tokens | 8.7 / 8 | 9.3 / 10 | -0.7 | -2 |
| output_tokens | 1655.3 / 1517 | 1680.7 / 1808 | -25.3 | -291 |
| cache_creation_input_tokens | 15154 / 15317 | 11669.3 / 11662 | +3484.7 | +3655 |
| cache_read_input_tokens | 161316.3 / 147189 | 165768.3 / 178612 | -4452 | -31423 |
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
| nothing-else-touched | 1/3 | 3/3 |
