# Eval report: embeddable-tool-pages

- Timestamp: 20261107T164239Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T164056Z-cb64fa; started 2026-11-07T16:42:39Z, ended 2026-11-07T16:48:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.56, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.84 over 6 call(s); agent $1.84, judge $0.00, guard $0.00; last agent call $0.27

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3371 / 1.0112 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.2747 / 0.8241 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3371 / 0.3355 | 0.2747 / 0.2715 | +0.0624 | +0.0641 |
| num_turns | 10 / 9 | 6.3 / 6 | +3.7 | +3 |
| duration_ms | 58097.3 / 63437 | 50716.3 / 51979 | +7381 | +11458 |
| input_tokens | 20.7 / 20 | 14.7 / 14 | +6 | +6 |
| output_tokens | 3308 / 3272 | 2900.7 / 2901 | +407.3 | +371 |
| cache_creation_input_tokens | 24589.3 / 21909 | 20193 / 20223 | +4396.3 | +1686 |
| cache_read_input_tokens | 360595.3 / 320373 | 244127 / 229388 | +116468.3 | +90985 |
| tool_errors | 1.7 / 1 | 0.3 / 0 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 1/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
