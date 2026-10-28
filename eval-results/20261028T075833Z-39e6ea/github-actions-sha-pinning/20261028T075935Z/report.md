# Eval report: github-actions-sha-pinning

- Timestamp: 20261028T075935Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T075833Z-39e6ea; started 2026-10-28T07:59:35Z, ended 2026-10-28T08:01:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.08, seven_day 0.26 to 0.27, from 10 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 9/10 | 4.1 (4.0 to 4.3, 3 judged) | 0.1807 / 0.5421 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1807 / 0.1819 |
| num_turns | 5 / 5 |
| duration_ms | 28844.7 / 28463 |
| input_tokens | 10 / 10 |
| output_tokens | 2305 / 2410 |
| cache_creation_input_tokens | 12308.3 / 12371 |
| cache_read_input_tokens | 179798.7 / 179542 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| third-party-actions-sha-pinned | 3/3 |
| third-party-pins-match-pins-md | 3/3 |
| no-trailing-comments | 0/3 |
| cms-platform-refs-stay-on-tag | 3/3 |
| local-and-docker-refs-untouched | 3/3 |
| reference-files-untouched | 3/3 |
| ci-workflow-not-deleted | 3/3 |
| deploy-workflow-not-deleted | 3/3 |
| gate-action-not-deleted | 3/3 |
| workflows-still-parse | 3/3 |
