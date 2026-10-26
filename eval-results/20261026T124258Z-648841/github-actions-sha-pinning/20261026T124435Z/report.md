# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T124435Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T124258Z-648841; started 2026-10-26T12:44:35Z, ended 2026-10-26T12:46:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.38 to 0.39, seven_day 0.65 to 0.65, from 7 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/10 | skipped (objective-decided) | 0.0985 / 0.2956 |
| without_skill | 3 | 0 | 8.7/10 | skipped (objective-decided) | 0.0845 / 0.2534 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0985 / 0.0845 | 0.0845 / 0.0814 | +0.0141 | +0.0031 |
| num_turns | 4 / 4 | 4.7 / 4 | -0.7 | 0 |
| duration_ms | 16303.7 / 14813 | 14806.7 / 15005 | +1497 | -192 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 1414.7 / 1399 | 1346 / 1280 | +68.7 | +119 |
| cache_creation_input_tokens | 17727 / 14316 | 13982 / 13709 | +3745 | +607 |
| cache_read_input_tokens | 134548.7 / 137981 | 150464.7 / 137497 | -15916 | +484 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 2/3 | 1/3 |
| third-party-pins-match-pins-md | 2/3 | 1/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
