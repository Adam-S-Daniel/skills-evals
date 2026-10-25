# Eval report: browser-testing

- Timestamp: 20261025T204923Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T204756Z-115f57; started 2026-10-25T20:49:23Z, ended 2026-10-25T21:12:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.1 to 0.14, seven_day 0.44 to 0.44, from 10 snapshots

## Fixture: browser-testing (n=3)

- Prompt: Add an e2e spec that proves the posts-list dashboard shows a draft's preview link, in the admin-read lane. Work within the supplied e2e harness.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2/9 | 8.8 (8.8 to 8.9, 3 judged) | 1.3082 / 3.9246 |
| without_skill | 3 | 0 | 2/9 | 8.4 (8.4 to 8.4, 1 judged); 2 judge error(s) | 1.0599 / 3.1797 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 1.3082 / 1.3465 | 1.0599 / 1.0425 | +0.2483 | +0.3040 |
| num_turns | 21 / 21 | 15.7 / 17 | +5.3 | +4 |
| duration_ms | 177363 / 168947 | 156441.7 / 157438 | +20921.3 | +11509 |
| input_tokens | 36 / 36 | 26.7 / 28 | +9.3 | +8 |
| output_tokens | 12091.3 / 12106 | 11473 / 11294 | +618.3 | +812 |
| cache_creation_input_tokens | 84979.3 / 86026 | 75806 / 74491 | +9173.3 | +11535 |
| cache_read_input_tokens | 1297270 / 1251386 | 879592.3 / 984382 | +417677.7 | +267004 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| new-spec | 0/3 | 0/3 |
| preview-link-assertion | 0/3 | 0/3 |
| admin-read | 0/3 | 0/3 |
| single-entry-after-publish | 0/3 | 0/3 |
| base-collection-guard | 0/3 | 0/3 |
| config-origin | 0/3 | 0/3 |
| consumer-spec | 0/3 | 0/3 |
| verifier-pinned | 3/3 | 3/3 |
| harness-unchanged | 3/3 | 3/3 |
