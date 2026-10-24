# Eval report: embeddable-tool-pages

- Timestamp: 20261024T234642Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261024T234508Z-b34cf1; started 2026-10-24T23:46:42Z, ended 2026-10-24T23:53:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.02, seven_day 0.36 to 0.36, from 7 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.3079 / 0.9237 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.3180 / 0.9541 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3079 / 0.3016 | 0.3180 / 0.3054 | -0.0101 | -0.0038 |
| num_turns | 17.7 / 16 | 18.7 / 19 | -1 | -3 |
| duration_ms | 65054.7 / 58505 | 66828 / 70191 | -1773.3 | -11686 |
| input_tokens | 26.7 / 26 | 28 / 24 | -1.3 | +2 |
| output_tokens | 3726 / 3482 | 5100.7 / 5317 | -1374.7 | -1835 |
| cache_creation_input_tokens | 34005.3 / 34031 | 32277 / 32558 | +1728.3 | +1473 |
| cache_read_input_tokens | 672766.7 / 653160 | 689241.7 / 593188 | -16475 | +59972 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| asset-copy | 3/3 | 3/3 |
| tool-front-matter | 3/3 | 3/3 |
| tool-entry-listing | 3/3 | 3/3 |
| post-embed | 3/3 | 0/3 |
| source-unchanged | 3/3 | 3/3 |
| existing-tool-unchanged | 3/3 | 3/3 |
| site-wiring-unchanged | 3/3 | 3/3 |
