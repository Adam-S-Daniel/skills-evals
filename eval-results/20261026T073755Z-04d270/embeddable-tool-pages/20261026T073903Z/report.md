# Eval report: embeddable-tool-pages

- Timestamp: 20261026T073903Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T073755Z-04d270; started 2026-10-26T07:39:03Z, ended 2026-10-26T07:41:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.17 to 0.17, seven_day 0.57 to 0.57, from 6 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1330 / 0.3991 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1078 / 0.3234 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1330 / 0.1018 | 0.1078 / 0.1119 | +0.0252 | -0.0101 |
| num_turns | 6.7 / 7 | 6.7 / 7 | 0 | 0 |
| duration_ms | 24952.3 / 26172 | 29025 / 29627 | -4072.7 | -3455 |
| input_tokens | 9.3 / 10 | 12.7 / 14 | -3.3 | -4 |
| output_tokens | 1429 / 1436 | 1871.7 / 1943 | -442.7 | -507 |
| cache_creation_input_tokens | 25589.7 / 17202 | 16441.3 / 16612 | +9148.3 | +590 |
| cache_read_input_tokens | 163689.3 / 161128 | 232874.7 / 259908 | -69185.3 | -98780 |
| tool_errors | 0 / 0 | 1.3 / 0 | -1.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
