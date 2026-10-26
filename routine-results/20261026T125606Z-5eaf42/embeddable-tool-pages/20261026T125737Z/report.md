# Eval report: embeddable-tool-pages

- Timestamp: 20261026T125737Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T125606Z-5eaf42; started 2026-10-26T12:57:37Z, ended 2026-10-26T13:03:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.43 to 0.01, seven_day 0.66 to 0.66, from 8 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.3432 / 1.0296 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.2801 / 0.8402 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3432 / 0.3584 | 0.2801 / 0.2827 | +0.0631 | +0.0757 |
| num_turns | 10.3 / 9 | 7 / 7 | +3.3 | +2 |
| duration_ms | 59642.3 / 43494 | 62183 / 57279 | -2540.7 | -13785 |
| input_tokens | 16.7 / 12 | 14 / 14 | +2.7 | -2 |
| output_tokens | 3518 / 3022 | 3287 / 3145 | +231 | -123 |
| cache_creation_input_tokens | 25402.3 / 24094 | 19614.7 / 19609 | +5787.7 | +4485 |
| cache_read_input_tokens | 337620.3 / 235277 | 268451.7 / 269149 | +69168.7 | -33872 |
| tool_errors | 2 / 1 | 1.3 / 2 | +0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 2/3 | 3/3 |
| tool-front-matter | 2/3 | 3/3 |
| tool-entry-listing | 2/3 | 3/3 |
| post-embed | 2/3 | 0/3 |
| source-unchanged | 3/3 | 1/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
