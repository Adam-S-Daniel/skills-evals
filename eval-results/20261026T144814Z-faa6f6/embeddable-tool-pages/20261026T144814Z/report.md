# Eval report: embeddable-tool-pages

- Timestamp: 20261026T144814Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144814Z-faa6f6; started 2026-10-26T14:48:14Z, ended 2026-10-26T14:55:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.6 to 0.67, seven_day 0.79 to 0.8, from 12 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3185 / 0.9555 |
| without_skill | 3 | 0 | 4.7/7 | skipped (objective-decided) | 0.2832 / 0.8496 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3185 / 0.3068 | 0.2832 / 0.2762 | +0.0353 | +0.0307 |
| num_turns | 8.7 / 9 | 7 / 7 | +1.7 | +2 |
| duration_ms | 53555 / 57691 | 79447.7 / 81918 | -25892.7 | -24227 |
| input_tokens | 14.7 / 14 | 14 / 14 | +0.7 | 0 |
| output_tokens | 3101 / 3056 | 3286 / 3395 | -185 | -339 |
| cache_creation_input_tokens | 24472.3 / 22478 | 19752 / 19686 | +4720.3 | +2792 |
| cache_read_input_tokens | 285819.7 / 281067 | 267407.3 / 266298 | +18412.3 | +14769 |
| tool_errors | 0.3 / 0 | 1.3 / 2 | -1 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 2/3 |
| tool-front-matter | 3/3 | 2/3 |
| tool-entry-listing | 3/3 | 2/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 2/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
