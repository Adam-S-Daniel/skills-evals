# Eval report: writing-adrs

- Timestamp: 20261026T144131Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144131Z-acfb5b; started 2026-10-26T14:41:31Z, ended 2026-10-26T14:46:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.55 to 0.57, seven_day 0.77 to 0.78, from 7 snapshots

## Fixture: why-no-comment-trail (n=3)

- Prompt: Why does scripts/export-ledger.sh end every CSV line with CRLF? There's no comment on it and nothing in the history says. I asked Priya, who wrote it: the bank's reconciliation importer rejects any file with bare LF line endings, and it's their tool, so we can't change it. Before that we exported LF and had finance run each file through a converter, but twice someone forgot and the month-end import failed. Converting in our upload job was ruled out too, because that job also uploads other exports that have to stay LF. Make sure the next person who wonders doesn't have to ask.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/11 | 9.1 (8.0 to 9.8, 3 judged) | 0.0944 / 0.2833 |
| without_skill | 3 | 0 | 11/11 | 9.3 (8.5 to 10.0, 3 judged) | 0.0844 / 0.2531 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0944 / 0.0945 | 0.0844 / 0.0832 | +0.0101 | +0.0113 |
| num_turns | 6 / 6 | 8 / 7 | -2 | -1 |
| duration_ms | 31612.7 / 28558 | 33298 / 35782 | -1685.3 | -7224 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 1770 / 1780 | 1922 / 1873 | -152 | -93 |
| cache_creation_input_tokens | 15468.7 / 15482 | 11786.3 / 11631 | +3682.3 | +3851 |
| cache_read_input_tokens | 146284.7 / 146312 | 177976 / 177743 | -31691.3 | -31431 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
| nothing-else-touched | 0/3 | 3/3 |
