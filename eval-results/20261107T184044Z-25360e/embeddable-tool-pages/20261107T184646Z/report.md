# Eval report: embeddable-tool-pages

- Timestamp: 20261107T184646Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184044Z-25360e; started 2026-11-07T18:46:46Z, ended 2026-11-07T18:49:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 6 call(s); agent $0.68, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1243 / 0.3730 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.1025 / 0.3075 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1243 / 0.1126 | 0.1025 / 0.0988 | +0.0218 | +0.0138 |
| num_turns | 7 / 7 | 6 / 5 | +1 | +2 |
| duration_ms | 24013.3 / 24317 | 24109.7 / 22900 | -96.3 | +1417 |
| input_tokens | 14 / 14 | 11.3 / 10 | +2.7 | +4 |
| output_tokens | 1678.7 / 1725 | 1745 / 1725 | -66.3 | 0 |
| cache_creation_input_tokens | 21274.3 / 17843 | 16075 / 15869 | +5199.3 | +1974 |
| cache_read_input_tokens | 224304 / 227766 | 207247 / 180357 | +17057 | +47409 |
| tool_errors | 0.7 / 0 | 0 / 0 | +0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
