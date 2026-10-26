# Eval report: embeddable-tool-pages

- Timestamp: 20261026T051420Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T051254Z-270099; started 2026-10-26T05:14:20Z, ended 2026-10-26T05:23:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.08 to 0.1, seven_day 0.55 to 0.55, from 8 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | 6.6 (3.4 to 8.2, 3 judged) | 0.3355 / 1.0065 |
| without_skill | 3 | 0 | 5.7/7 | 4.5 (3.3 to 5.3, 3 judged) | 0.2757 / 0.8270 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3355 / 0.3552 | 0.2757 / 0.2745 | +0.0598 | +0.0807 |
| num_turns | 10.3 / 10 | 7 / 7 | +3.3 | +3 |
| duration_ms | 58737.7 / 48017 | 59412.3 / 60486 | -674.7 | -12469 |
| input_tokens | 17.3 / 16 | 14 / 14 | +3.3 | +2 |
| output_tokens | 3175 / 2638 | 3131.7 / 3212 | +43.3 | -574 |
| cache_creation_input_tokens | 24957 / 24197 | 19432 / 19793 | +5525 | +4404 |
| cache_read_input_tokens | 349218.3 / 305313 | 268934.3 / 270741 | +80284 | +34572 |
| tool_errors | 2 / 1 | 0.3 / 0 | +1.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 2/3 | 3/3 |
| tool-front-matter | 2/3 | 3/3 |
| tool-entry-listing | 2/3 | 3/3 |
| post-embed | 2/3 | 0/3 |
| source-unchanged | 3/3 | 2/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
