# Eval report: finding-unknowns

- Timestamp: 20261026T144218Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144218Z-175052; started 2026-10-26T14:42:18Z, ended 2026-10-26T14:47:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.55 to 0.59, seven_day 0.78 to 0.78, from 9 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/4 | - | 0.2469 / 0.7408 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.1824 / 0.5471 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2469 / 0.2214 | 0.1824 / 0.1830 | +0.0645 | +0.0384 |
| num_turns | 7.7 / 8 | 6 / 6 | +1.7 | +2 |
| duration_ms | 49702.3 / 47799 | 45329 / 49029 | +4373.3 | -1230 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 3183 / 3159 | 2391.3 / 2409 | +791.7 | +750 |
| cache_creation_input_tokens | 18196 / 14969 | 11911.7 / 11827 | +6284.3 | +3142 |
| cache_read_input_tokens | 188244.3 / 194672 | 196063 / 196108 | -7818.7 | -1436 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 2/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
