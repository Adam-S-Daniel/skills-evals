# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T073913Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T073756Z-7fc084; started 2026-10-26T07:39:13Z, ended 2026-10-26T07:41:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.17 to 0.17, seven_day 0.57 to 0.57, from 6 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/10 | skipped (objective-decided) | 0.1032 / 0.3097 |
| without_skill | 3 | 0 | 8/10 | skipped (objective-decided) | 0.0818 / 0.2454 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1032 / 0.1020 | 0.0818 / 0.0813 | +0.0214 | +0.0207 |
| num_turns | 5 / 4 | 4.3 / 4 | +0.7 | 0 |
| duration_ms | 16643.7 / 15476 | 18928.3 / 19055 | -2284.7 | -3579 |
| input_tokens | 9.3 / 8 | 8 / 8 | +1.3 | 0 |
| output_tokens | 1440.7 / 1282 | 1241.7 / 1239 | +199 | +43 |
| cache_creation_input_tokens | 18169.7 / 15642 | 13895.7 / 13781 | +4274 | +1861 |
| cache_read_input_tokens | 161199 / 138509 | 137976.7 / 137885 | +23222.3 | +624 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 2/3 | 0/3 |
| third-party-pins-match-pins-md | 2/3 | 0/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
