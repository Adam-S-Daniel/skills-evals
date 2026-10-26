# Eval report: writing-adrs

- Timestamp: 20261026T140257Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140208Z-d1abe4; started 2026-10-26T14:02:57Z, ended 2026-10-26T14:06:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.25 to 0.28, seven_day 0.71 to 0.71, from 8 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | 10.0 (10.0 to 10.0, 3 judged) | 0.1839 / 0.5517 |
| without_skill | 3 | 0 | 11/11 | 9.7 (9.5 to 10.0, 3 judged) | 0.1515 / 0.4545 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1839 / 0.1851 | 0.1515 / 0.1523 | +0.0324 | +0.0329 |
| num_turns | 6.3 / 6 | 4 / 4 | +2.3 | +2 |
| duration_ms | 34054.3 / 22775 | 19584.3 / 19346 | +14470 | +3429 |
| input_tokens | 7.3 / 8 | 6.7 / 6 | +0.7 | +2 |
| output_tokens | 1597 / 1597 | 1448 / 1500 | +149 | +97 |
| cache_creation_input_tokens | 15634.7 / 15674 | 12406.7 / 12393 | +3228 | +3281 |
| cache_read_input_tokens | 133553.3 / 147151 | 115368.7 / 103087 | +18184.7 | +44064 |
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
