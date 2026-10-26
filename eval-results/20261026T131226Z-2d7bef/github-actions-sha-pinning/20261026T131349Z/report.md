# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T131349Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T131226Z-2d7bef; started 2026-10-26T13:13:49Z, ended 2026-10-26T13:21:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.03 to 0.05, seven_day 0.67 to 0.67, from 8 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | skipped (objective-decided) | 0.3207 / 0.9620 |
| without_skill | 3 | 0 | 9/10 | skipped (objective-decided) | 0.3098 / 0.9294 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3207 / 0.3060 | 0.3098 / 0.3327 | +0.0109 | -0.0267 |
| num_turns | 6.3 / 6 | 8 / 8 | -1.7 | -2 |
| duration_ms | 63626 / 62806 | 80490 / 86033 | -16864 | -23227 |
| input_tokens | 12.7 / 12 | 16 / 16 | -3.3 | -4 |
| output_tokens | 4286.3 / 4475 | 4458.7 / 4837 | -172.3 | -362 |
| cache_creation_input_tokens | 22846.3 / 19717 | 19324 / 19957 | +3522.3 | -240 |
| cache_read_input_tokens | 233162.3 / 221304 | 303645.7 / 304412 | -70483.3 | -83108 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 3/3 | 2/3 |
| third-party-pins-match-pins-md | 3/3 | 2/3 |
| no-trailing-comments | 3/3 | 2/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
