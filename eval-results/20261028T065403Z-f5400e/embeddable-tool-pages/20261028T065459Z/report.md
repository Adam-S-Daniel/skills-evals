# Eval report: embeddable-tool-pages

- Timestamp: 20261028T065459Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T065403Z-f5400e; started 2026-10-28T06:54:59Z, ended 2026-10-28T06:58:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.05 to 0.06, seven_day 0.26 to 0.26, from 9 snapshots

## Fixture: embeddable-tool-pages (n=3)

- Prompt: Publish seed/new-tool as a Tools page at /tools/unit-converter/ and embed it in the post _posts/2026-01-01-example.md below the intro.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6/7 | 4.8 (4.5 to 5.0, 3 judged) | 0.1799 / 0.5396 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1799 / 0.1835 |
| num_turns | 6 / 6 |
| duration_ms | 23880.7 / 23852 |
| input_tokens | 11.3 / 12 |
| output_tokens | 1823.3 / 1858 |
| cache_creation_input_tokens | 12678.3 / 12684 |
| cache_read_input_tokens | 208778 / 221795 |
| tool_errors | 1.3 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| asset-copy | 3/3 |
| tool-front-matter | 3/3 |
| tool-entry-listing | 3/3 |
| post-embed | 0/3 |
| source-unchanged | 3/3 |
| existing-tool-unchanged | 3/3 |
| site-wiring-unchanged | 3/3 |
