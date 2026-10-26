# Eval report: embeddable-tool-pages

- Timestamp: 20261026T092244Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T092131Z-f5c14e; started 2026-10-26T09:22:44Z, ended 2026-10-26T09:28:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.03 to 0.04, seven_day 0.58 to 0.58, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3233 / 0.9700 |
| without_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.2948 / 0.8845 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3233 / 0.2936 | 0.2948 / 0.2858 | +0.0285 | +0.0078 |
| num_turns | 9.7 / 9 | 7 / 7 | +2.7 | +2 |
| duration_ms | 50147 / 43918 | 65643 / 64359 | -15496 | -20441 |
| input_tokens | 15.3 / 16 | 14 / 14 | +1.3 | +2 |
| output_tokens | 3197 / 3027 | 3594 / 3335 | -397 | -308 |
| cache_creation_input_tokens | 24625.7 / 22449 | 20397.3 / 19986 | +4228.3 | +2463 |
| cache_read_input_tokens | 301554.7 / 315343 | 269887 / 268703 | +31667.7 | +46640 |
| tool_errors | 1.7 / 2 | 0.3 / 0 | +1.3 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 2/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
