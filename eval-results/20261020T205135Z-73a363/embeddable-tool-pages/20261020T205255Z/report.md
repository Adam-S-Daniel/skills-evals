# Eval report: embeddable-tool-pages

- Timestamp: 20261020T205255Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261020T205135Z-73a363; started 2026-10-20T20:52:55Z, ended 2026-10-20T20:55:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.1 to 0.1, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.304 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1466 / 0.4398 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1437 / 0.4311 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1466 / 0.1390 | 0.1437 / 0.1430 | +0.0029 | -0.0040 |
| num_turns | 6.7 / 6 | 5.7 / 6 | +1 | 0 |
| duration_ms | 27938.3 / 24481 | 28135.7 / 28857 | -197.3 | -4376 |
| input_tokens | 10 / 8 | 11.3 / 12 | -1.3 | -4 |
| output_tokens | 1590 / 1438 | 1640.3 / 1652 | -50.3 | -214 |
| cache_creation_input_tokens | 28485 / 28071 | 27162.3 / 26816 | +1322.7 | +1255 |
| cache_read_input_tokens | 167312.3 / 126760 | 186307.7 / 197333 | -18995.3 | -70573 |
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
