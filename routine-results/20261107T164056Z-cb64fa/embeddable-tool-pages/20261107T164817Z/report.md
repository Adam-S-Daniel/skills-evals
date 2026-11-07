# Eval report: embeddable-tool-pages

- Timestamp: 20261107T164817Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T164056Z-cb64fa; started 2026-11-07T16:48:17Z, ended 2026-11-07T16:51:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 6 call(s); agent $0.69, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1247 / 0.3740 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1057 / 0.3171 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1247 / 0.1182 | 0.1057 / 0.0953 | +0.0190 | +0.0229 |
| num_turns | 7.3 / 8 | 6.3 / 6 | +1 | +2 |
| duration_ms | 31627 / 26422 | 27362 / 20878 | +4265 | +5544 |
| input_tokens | 14 / 16 | 12 / 10 | +2 | +6 |
| output_tokens | 1690.3 / 1796 | 1763 / 1452 | -72.7 | +344 |
| cache_creation_input_tokens | 21300.3 / 18270 | 16450.7 / 15690 | +4849.7 | +2580 |
| cache_read_input_tokens | 225329.7 / 260396 | 222581.3 / 179812 | +2748.3 | +80584 |
| tool_errors | 0.7 / 1 | 1.3 / 1 | -0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
