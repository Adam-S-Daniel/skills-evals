# Eval report: writing-adrs

- Timestamp: 20261026T065033Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T064934Z-bca5a2; started 2026-10-26T06:50:33Z, ended 2026-10-26T06:53:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.13 to 0.13, seven_day 0.56 to 0.56, from 6 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | 9.8 (9.5 to 10.0, 3 judged) | 0.1932 / 0.5797 |
| without_skill | 3 | 0 | 11/11 | 9.8 (9.5 to 10.0, 3 judged) | 0.1522 / 0.4567 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1932 / 0.1915 | 0.1522 / 0.1517 | +0.0410 | +0.0398 |
| num_turns | 6.7 / 7 | 3.3 / 3 | +3.3 | +4 |
| duration_ms | 23348 / 22686 | 19245.3 / 18846 | +4102.7 | +3840 |
| input_tokens | 8 / 8 | 6.7 / 6 | +1.3 | +2 |
| output_tokens | 1827 / 1796 | 1494.3 / 1492 | +332.7 | +304 |
| cache_creation_input_tokens | 15860.7 / 15736 | 12383.3 / 12526 | +3477.3 | +3210 |
| cache_read_input_tokens | 148184.7 / 147601 | 115370.3 / 103083 | +32814.3 | +44518 |
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
