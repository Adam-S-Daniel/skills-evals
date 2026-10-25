# Eval report: github-actions-sha-pinning

- Timestamp: 20261025T204905Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T204757Z-c08b54; started 2026-10-25T20:49:05Z, ended 2026-10-25T20:58:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.1 to 0.12, seven_day 0.44 to 0.44, from 8 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/10 | 8.8 (8.3 to 9.3, 3 judged) | 0.3377 / 1.0130 |
| without_skill | 3 | 0 | 9/10 | 9.3 (8.9 to 9.7, 3 judged) | 0.3033 / 0.9099 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3377 / 0.3277 | 0.3033 / 0.3060 | +0.0344 | +0.0216 |
| num_turns | 7.7 / 8 | 7.3 / 7 | +0.3 | +1 |
| duration_ms | 81099.3 / 87608 | 75407.3 / 76497 | +5692 | +11111 |
| input_tokens | 15.3 / 16 | 14 / 14 | +1.3 | +2 |
| output_tokens | 4399.7 / 4480 | 4420.3 / 4562 | -20.7 | -82 |
| cache_creation_input_tokens | 23214.7 / 20299 | 19555 / 19155 | +3659.7 | +1144 |
| cache_read_input_tokens | 290110.7 / 300292 | 264149.3 / 262810 | +25961.3 | +37482 |
| tool_errors | 0.7 / 0 | 0.7 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 1/3 | 2/3 |
| third-party-pins-match-pins-md | 1/3 | 2/3 |
| no-trailing-comments | 1/3 | 2/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
