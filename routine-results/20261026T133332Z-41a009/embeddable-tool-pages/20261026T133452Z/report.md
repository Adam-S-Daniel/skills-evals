# Eval report: embeddable-tool-pages

- Timestamp: 20261026T133452Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133332Z-41a009; started 2026-10-26T13:34:52Z, ended 2026-10-26T13:37:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.68 to 0.68, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1097 / 0.3292 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1070 / 0.3210 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1097 / 0.0969 | 0.1070 / 0.1091 | +0.0027 | -0.0122 |
| num_turns | 6 / 6 | 6.7 / 7 | -0.7 | -1 |
| duration_ms | 14575 / 13208 | 26599.7 / 25409 | -12024.7 | -12201 |
| input_tokens | 8 / 8 | 13.3 / 14 | -5.3 | -6 |
| output_tokens | 1297.7 / 1312 | 1806.7 / 1800 | -509 | -488 |
| cache_creation_input_tokens | 20671.3 / 17325 | 16093.3 / 16078 | +4578 | +1247 |
| cache_read_input_tokens | 140556.7 / 143995 | 245205.7 / 258480 | -104649 | -114485 |
| tool_errors | 0.7 / 1 | 1 / 1 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
