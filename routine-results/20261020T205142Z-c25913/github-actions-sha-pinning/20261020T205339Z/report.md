# Eval report: github-actions-sha-pinning

- Timestamp: 20261020T205339Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261020T205142Z-c25913; started 2026-10-20T20:53:39Z, ended 2026-10-20T20:56:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.1 to 0.1, from 7 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.304 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 8.8 (8.5 to 8.9, 3 judged) | 0.1269 / 0.3808 |
| without_skill | 3 | 0 | 10/10 | 9.0 (8.8 to 9.2, 3 judged) | 0.1287 / 0.3861 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1269 / 0.1266 | 0.1287 / 0.1266 | -0.0017 | 0 |
| num_turns | 4 / 4 | 4.3 / 4 | -0.3 | 0 |
| duration_ms | 23255.7 / 21428 | 19080 / 19013 | +4175.7 | +2415 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 1319.3 / 1315 | 1444.3 / 1376 | -125 | -61 |
| cache_creation_input_tokens | 25397 / 25306 | 25232.3 / 25182 | +164.7 | +124 |
| cache_read_input_tokens | 121416.3 / 121142 | 132985.7 / 120738 | -11569.3 | +404 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 3/3 | 3/3 |
| third-party-pins-match-pins-md | 3/3 | 3/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
