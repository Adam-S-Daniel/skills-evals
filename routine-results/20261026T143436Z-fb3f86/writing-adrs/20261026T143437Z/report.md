# Eval report: writing-adrs

- Timestamp: 20261026T143437Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143436Z-fb3f86; started 2026-10-26T14:34:37Z, ended 2026-10-26T14:39:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.5 to 0.53, seven_day 0.76 to 0.77, from 10 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10.7/11 | 9.8 (9.4 to 10.0, 3 judged) | 0.0968 / 0.2904 |
| without_skill | 3 | 0 | 10.7/11 | 9.7 (9.0 to 10.0, 3 judged) | 0.0770 / 0.2311 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0968 / 0.0953 | 0.0770 / 0.0731 | +0.0198 | +0.0222 |
| num_turns | 7.7 / 8 | 5.7 / 4 | +2 | +4 |
| duration_ms | 28795 / 28176 | 26949 / 24380 | +1846 | +3796 |
| input_tokens | 8.7 / 8 | 8.7 / 8 | 0 | 0 |
| output_tokens | 1931 / 1956 | 1541.7 / 1430 | +389.3 | +526 |
| cache_creation_input_tokens | 15313.7 / 15370 | 11545.7 / 11406 | +3768 | +3964 |
| cache_read_input_tokens | 160629.3 / 146410 | 152302 / 138992 | +8327.3 | +7418 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

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
| nothing-else-touched | 2/3 | 2/3 |
