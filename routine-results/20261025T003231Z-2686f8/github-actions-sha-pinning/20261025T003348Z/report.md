# Eval report: github-actions-sha-pinning

- Timestamp: 20261025T003348Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T003231Z-2686f8; started 2026-10-25T00:33:48Z, ended 2026-10-25T00:43:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.04 to 0.06, seven_day 0.36 to 0.37, from 9 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 8.9 (8.9 to 8.9, 3 judged) | 0.2877 / 0.8630 |
| without_skill | 3 | 0 | 10/10 | 9.2 (8.9 to 9.3, 3 judged) | 0.3049 / 0.9147 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2877 / 0.3041 | 0.3049 / 0.2764 | -0.0172 | +0.0277 |
| num_turns | 13 / 12 | 13.3 / 14 | -0.3 | -2 |
| duration_ms | 86363 / 98070 | 80004 / 80717 | +6359 | +17353 |
| input_tokens | 20.7 / 24 | 21.3 / 20 | -0.7 | +4 |
| output_tokens | 5975.7 / 5982 | 5901.3 / 5760 | +74.3 | +222 |
| cache_creation_input_tokens | 32272.7 / 32251 | 34945.3 / 31054 | -2672.7 | +1197 |
| cache_read_input_tokens | 493972.3 / 576169 | 530319 / 472700 | -36346.7 | +103469 |
| tool_errors | 0.3 / 0 | 1.7 / 2 | -1.3 | -2 |

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
