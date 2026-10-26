# Eval report: writing-adrs

- Timestamp: 20261026T140255Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140204Z-f66515; started 2026-10-26T14:02:55Z, ended 2026-10-26T14:06:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.25 to 0.28, seven_day 0.71 to 0.71, from 9 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/11 | 9.0 (8.2 to 9.4, 3 judged) | 0.0933 / 0.2798 |
| without_skill | 3 | 0 | 10.7/11 | 9.6 (9.4 to 10.0, 3 judged) | 0.0805 / 0.2414 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0933 / 0.0931 | 0.0805 / 0.0819 | +0.0128 | +0.0112 |
| num_turns | 6 / 6 | 6 / 7 | 0 | -1 |
| duration_ms | 29666 / 29981 | 22373 / 23622 | +7293 | +6359 |
| input_tokens | 8 / 8 | 9.3 / 10 | -1.3 | -2 |
| output_tokens | 1681.3 / 1680 | 1722 / 1764 | -40.7 | -84 |
| cache_creation_input_tokens | 15373.7 / 15394 | 11617.3 / 11625 | +3756.3 | +3769 |
| cache_read_input_tokens | 147210 / 147222 | 165564.7 / 178447 | -18354.7 | -31225 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

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
| nothing-else-touched | 0/3 | 2/3 |
