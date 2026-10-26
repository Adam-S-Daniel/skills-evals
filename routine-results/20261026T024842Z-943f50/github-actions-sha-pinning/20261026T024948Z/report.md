# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T024948Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T024842Z-943f50; started 2026-10-26T02:49:48Z, ended 2026-10-26T02:52:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.23 to 0.23, seven_day 0.53 to 0.53, from 6 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/10 | 9.2 (8.8 to 9.6, 3 judged) | 0.0961 / 0.2884 |
| without_skill | 3 | 0 | 8/10 | 9.1 (8.8 to 9.2, 3 judged) | 0.0805 / 0.2415 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0961 / 0.0817 | 0.0805 / 0.0806 | +0.0156 | +0.0011 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 16676 / 17890 | 14544.7 / 14666 | +2131.3 | +3224 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 1354.3 / 1303 | 1285 / 1277 | +69.3 | +26 |
| cache_creation_input_tokens | 17292.3 / 13746 | 13488 / 13518 | +3804.3 | +228 |
| cache_read_input_tokens | 134140.7 / 137551 | 136881.3 / 136945 | -2740.7 | +606 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 0/3 | 0/3 |
| third-party-pins-match-pins-md | 0/3 | 0/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
