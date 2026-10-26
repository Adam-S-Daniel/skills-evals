# Eval report: embeddable-tool-pages

- Timestamp: 20261026T121512Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T121351Z-a15b20; started 2026-10-26T12:15:12Z, ended 2026-10-26T12:21:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.25 to 0.27, seven_day 0.62 to 0.63, from 8 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3197 / 0.9590 |
| without_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.2714 / 0.8142 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3197 / 0.3030 | 0.2714 / 0.2724 | +0.0483 | +0.0306 |
| num_turns | 8.7 / 8 | 6 / 6 | +2.7 | +2 |
| duration_ms | 57434.3 / 59937 | 60723 / 57583 | -3288.7 | +2354 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3127 / 3061 | 3122.3 / 3133 | +4.7 | -72 |
| cache_creation_input_tokens | 24751 / 21905 | 19753 / 19765 | +4998 | +2140 |
| cache_read_input_tokens | 271784.3 / 273379 | 226060.3 / 225912 | +45724 | +47467 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 2/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
