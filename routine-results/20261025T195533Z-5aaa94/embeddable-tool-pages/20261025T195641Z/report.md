# Eval report: embeddable-tool-pages

- Timestamp: 20261025T195641Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T195533Z-5aaa94; started 2026-10-25T19:56:41Z, ended 2026-10-25T20:03:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.07, seven_day 0.43 to 0.43, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.2997 / 0.8991 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.3032 / 0.9097 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2997 / 0.2801 | 0.3032 / 0.2881 | -0.0035 | -0.0080 |
| num_turns | 8 / 8 | 7.3 / 7 | +0.7 | +1 |
| duration_ms | 53408.7 / 53781 | 73334.3 / 81861 | -19925.7 | -28080 |
| input_tokens | 14 / 14 | 14.7 / 14 | -0.7 | 0 |
| output_tokens | 2902 / 2904 | 3738.3 / 3370 | -836.3 | -466 |
| cache_creation_input_tokens | 23464.3 / 20272 | 20702 / 20130 | +2762.3 | +142 |
| cache_read_input_tokens | 269378.3 / 272383 | 284532 / 268982 | -15153.7 | +3401 |
| tool_errors | 1.7 / 2 | 0.3 / 0 | +1.3 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
