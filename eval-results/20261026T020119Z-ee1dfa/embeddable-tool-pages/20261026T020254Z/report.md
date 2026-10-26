# Eval report: embeddable-tool-pages

- Timestamp: 20261026T020254Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T020119Z-ee1dfa; started 2026-10-26T02:02:54Z, ended 2026-10-26T02:05:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.19 to 0.2, seven_day 0.52 to 0.52, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1129 / 0.3387 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1106 / 0.3318 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1129 / 0.1039 | 0.1106 / 0.1119 | +0.0023 | -0.0080 |
| num_turns | 6.3 / 6 | 7.3 / 8 | -1 | -2 |
| duration_ms | 17335.7 / 16563 | 25713.7 / 24563 | -8378 | -8000 |
| input_tokens | 8.7 / 8 | 14 / 14 | -5.3 | -6 |
| output_tokens | 1451.3 / 1461 | 1945 / 1942 | -493.7 | -481 |
| cache_creation_input_tokens | 20732 / 17549 | 16301.7 / 16627 | +4430.3 | +922 |
| cache_read_input_tokens | 154315.3 / 143823 | 259147.3 / 259411 | -104832 | -115588 |
| tool_errors | 0.3 / 0 | 2.3 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
