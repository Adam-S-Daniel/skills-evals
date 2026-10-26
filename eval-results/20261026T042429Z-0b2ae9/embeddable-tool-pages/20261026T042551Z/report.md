# Eval report: embeddable-tool-pages

- Timestamp: 20261026T042551Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T042429Z-0b2ae9; started 2026-10-26T04:25:51Z, ended 2026-10-26T04:28:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.07 to 0.08, seven_day 0.55 to 0.55, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1195 / 0.3586 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1036 / 0.3108 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1195 / 0.1253 | 0.1036 / 0.1047 | +0.0159 | +0.0206 |
| num_turns | 8.7 / 6 | 6.3 / 7 | +2.3 | -1 |
| duration_ms | 32955.3 / 19809 | 25927 / 26499 | +7028.3 | -6690 |
| input_tokens | 10.7 / 8 | 12.7 / 14 | -2 | -6 |
| output_tokens | 1564.7 / 1425 | 1711.7 / 1659 | -147 | -234 |
| cache_creation_input_tokens | 21064.7 / 18463 | 15831.7 / 15723 | +5233 | +2740 |
| cache_read_input_tokens | 196124 / 143805 | 231476 / 257813 | -35352 | -114008 |
| tool_errors | 2 / 1 | 1.7 / 2 | +0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
