# Eval report: embeddable-tool-pages

- Timestamp: 20261107T184222Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184044Z-25360e; started 2026-11-07T18:42:22Z, ended 2026-11-07T18:46:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.71 over 6 call(s); agent $1.71, judge $0.00, guard $0.00; last agent call $0.26

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.2994 / 0.8983 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.2697 / 0.8091 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2994 / 0.2794 | 0.2697 / 0.2735 | +0.0297 | +0.0059 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 35449.7 / 32072 | 49088.3 / 51319 | -13638.7 | -19247 |
| input_tokens | 17.3 / 18 | 14.7 / 14 | +2.7 | +4 |
| output_tokens | 2741.7 / 2844 | 3010.3 / 3076 | -268.7 | -232 |
| cache_creation_input_tokens | 23102.7 / 19869 | 19137.3 / 18883 | +3965.3 | +986 |
| cache_read_input_tokens | 298515.7 / 316322 | 270434.7 / 270388 | +28081 | +45934 |
| tool_errors | 1.3 / 1 | 1 / 1 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 2/3 | 1/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
