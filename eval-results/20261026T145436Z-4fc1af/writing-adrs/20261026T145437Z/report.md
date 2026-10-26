# Eval report: writing-adrs

- Timestamp: 20261026T145437Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145436Z-4fc1af; started 2026-10-26T14:54:37Z, ended 2026-10-26T14:58:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.66 to 0.68, seven_day 0.8 to 0.8, from 7 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10.3/11 | 9.7 (9.0 to 10.0, 3 judged) | 0.0916 / 0.2747 |
| without_skill | 3 | 0 | 10.7/11 | 9.3 (8.5 to 10.0, 3 judged) | 0.0804 / 0.2413 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0916 / 0.0918 | 0.0804 / 0.0824 | +0.0111 | +0.0094 |
| num_turns | 6 / 6 | 6 / 7 | 0 | -1 |
| duration_ms | 18579.3 / 18551 | 20094.3 / 19558 | -1515 | -1007 |
| input_tokens | 8 / 8 | 9.3 / 10 | -1.3 | -2 |
| output_tokens | 1584 / 1589 | 1712.3 / 1800 | -128.3 | -211 |
| cache_creation_input_tokens | 15218.7 / 15267 | 11665 / 11651 | +3553.7 | +3616 |
| cache_read_input_tokens | 146252.3 / 146222 | 164672.3 / 177370 | -18420 | -31148 |
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
| nothing-else-touched | 1/3 | 2/3 |
