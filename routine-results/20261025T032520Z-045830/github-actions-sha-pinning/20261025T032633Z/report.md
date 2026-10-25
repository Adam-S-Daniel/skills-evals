# Eval report: github-actions-sha-pinning

- Timestamp: 20261025T032633Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T032520Z-045830; started 2026-10-25T03:26:33Z, ended 2026-10-25T03:34:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.18, seven_day 0.39 to 0.39, from 7 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | 8.9 (8.9 to 8.9, 3 judged) | 0.3019 / 0.9058 |
| without_skill | 3 | 0 | 10/10 | 9.2 (8.9 to 9.3, 3 judged) | 0.2687 / 0.8062 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3019 / 0.2747 | 0.2687 / 0.2705 | +0.0332 | +0.0042 |
| num_turns | 6.3 / 7 | 6 / 6 | +0.3 | +1 |
| duration_ms | 54811.7 / 45503 | 61516 / 61622 | -6704.3 | -16119 |
| input_tokens | 12.7 / 14 | 12 / 12 | +0.7 | +2 |
| output_tokens | 3772 / 3704 | 3419 / 3577 | +353 | +127 |
| cache_creation_input_tokens | 22146.3 / 18472 | 18840.7 / 18702 | +3305.7 | -230 |
| cache_read_input_tokens | 234341.3 / 259736 | 222360.3 / 222292 | +11981 | +37444 |
| tool_errors | 0.7 / 1 | 1 / 1 | -0.3 | 0 |

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
