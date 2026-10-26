# Eval report: embeddable-tool-pages

- Timestamp: 20261026T135332Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135208Z-4b6017; started 2026-10-26T13:53:32Z, ended 2026-10-26T13:56:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.2, seven_day 0.69 to 0.7, from 10 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1152 / 0.3456 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1093 / 0.3280 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1152 / 0.1049 | 0.1093 / 0.1093 | +0.0059 | -0.0044 |
| num_turns | 6.7 / 7 | 7.3 / 7 | -0.7 | 0 |
| duration_ms | 18358.7 / 20512 | 33370.7 / 26650 | -15012 | -6138 |
| input_tokens | 9.3 / 10 | 14 / 14 | -4.7 | -4 |
| output_tokens | 1492.3 / 1572 | 1811.7 / 1835 | -319.3 | -263 |
| cache_creation_input_tokens | 20858 / 17583 | 16314 / 16269 | +4544 | +1314 |
| cache_read_input_tokens | 168177.3 / 175148 | 259293.7 / 259724 | -91116.3 | -84576 |
| tool_errors | 0.7 / 1 | 1.3 / 2 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
