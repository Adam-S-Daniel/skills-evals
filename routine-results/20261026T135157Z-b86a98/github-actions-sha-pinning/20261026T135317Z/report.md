# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T135317Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135157Z-b86a98; started 2026-10-26T13:53:17Z, ended 2026-10-26T13:55:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.16 to 0.19, seven_day 0.69 to 0.69, from 7 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.7/10 | 9.0 (8.8 to 9.2, 3 judged) | 0.0971 / 0.2913 |
| without_skill | 3 | 0 | 8.7/10 | 9.2 (9.2 to 9.2, 3 judged) | 0.0830 / 0.2489 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0971 / 0.0866 | 0.0830 / 0.0818 | +0.0141 | +0.0049 |
| num_turns | 4.3 / 4 | 4.3 / 4 | 0 | 0 |
| duration_ms | 18453.3 / 17573 | 19678.7 / 16188 | -1225.3 | +1385 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 1346 / 1320 | 1364 / 1330 | -18 | -10 |
| cache_creation_input_tokens | 17542.3 / 14510 | 13894.7 / 13701 | +3647.7 | +809 |
| cache_read_input_tokens | 134629.7 / 138083 | 137481.3 / 137449 | -2851.7 | +634 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 1/3 | 1/3 |
| third-party-pins-match-pins-md | 1/3 | 1/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
