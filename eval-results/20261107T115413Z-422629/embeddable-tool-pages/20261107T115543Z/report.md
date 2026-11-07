# Eval report: embeddable-tool-pages

- Timestamp: 20261107T115543Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T115413Z-422629; started 2026-11-07T11:55:43Z, ended 2026-11-07T11:57:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 4 call(s); agent $0.47, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: embeddable-tool-pages (n=2)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1308 / 0.2615 |
| without_skill | 2 | 0 | 6/7 | skipped (objective-decided) | 0.1046 / 0.2091 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1308 / 0.1308 | 0.1046 / 0.1046 | +0.0262 | +0.0262 |
| num_turns | 7.5 / 7.5 | 6 / 6 | +1.5 | +1.5 |
| duration_ms | 21574 / 21574 | 18136.5 / 18136.5 | +3437.5 | +3437.5 |
| input_tokens | 15 / 15 | 12 / 12 | +3 | +3 |
| output_tokens | 1505.5 / 1505.5 | 1745.5 / 1745.5 | -240 | -240 |
| cache_creation_input_tokens | 22850 / 22850 | 16259 / 16259 | +6591 | +6591 |
| cache_read_input_tokens | 242857 / 242857 | 220551 / 220551 | +22306 | +22306 |
| tool_errors | 1.5 / 1.5 | 1.5 / 1.5 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 2/2 | 2/2 |
| tool-front-matter | 2/2 | 2/2 |
| tool-entry-listing | 2/2 | 2/2 |
| post-embed | 2/2 | 0/2 |
| source-unchanged | 2/2 | 2/2 |
| existing-tool-unchanged | 2/2 | 2/2 |
| site-wiring-unchanged | 2/2 | 2/2 |
