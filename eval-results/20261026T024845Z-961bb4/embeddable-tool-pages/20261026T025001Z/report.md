# Eval report: embeddable-tool-pages

- Timestamp: 20261026T025001Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T024845Z-961bb4; started 2026-10-26T02:50:01Z, ended 2026-10-26T02:56:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.23 to 0.24, seven_day 0.53 to 0.53, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3122 / 0.9365 |
| without_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.2810 / 0.8430 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3122 / 0.3058 | 0.2810 / 0.2849 | +0.0312 | +0.0210 |
| num_turns | 8.3 / 8 | 6.7 / 7 | +1.7 | +1 |
| duration_ms | 52807.3 / 55226 | 64555.7 / 66958 | -11748.3 | -11732 |
| input_tokens | 14 / 14 | 13.3 / 14 | +0.7 | 0 |
| output_tokens | 3030 / 3007 | 3202.7 / 3160 | -172.7 | -153 |
| cache_creation_input_tokens | 24333 / 21804 | 20031 / 20257 | +4302 | +1547 |
| cache_read_input_tokens | 272671.7 / 262691 | 254715 / 268104 | +17956.7 | -5413 |
| tool_errors | 1 / 1 | 1 / 0 | 0 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 2/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
