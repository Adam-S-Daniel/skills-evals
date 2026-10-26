# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T144727Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144727Z-0c2277; started 2026-10-26T14:47:27Z, ended 2026-10-26T14:54:33Z
- Budget stop: per_run_cap (limit 0.015, weekly meter 0.8, moved 0.02); no trial or judge call started after it
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.59 to 0.66, seven_day 0.78 to 0.8, from 9 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/10 | error | 0.3084 / 0.9253 |
| without_skill | 3 | 0 | 9.3/10 | error | 0.3060 / 0.9179 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3084 / 0.3001 | 0.3060 / 0.3089 | +0.0025 | -0.0088 |
| num_turns | 6.7 / 6 | 7.3 / 7 | -0.7 | -1 |
| duration_ms | 62886.7 / 63929 | 72509 / 73021 | -9622.3 | -9092 |
| input_tokens | 13.3 / 12 | 14.7 / 14 | -1.3 | -2 |
| output_tokens | 3793 / 3715 | 4566.7 / 4671 | -773.7 | -956 |
| cache_creation_input_tokens | 22235.3 / 19210 | 19288 / 19204 | +2947.3 | +6 |
| cache_read_input_tokens | 245779.7 / 221901 | 276798.7 / 261932 | -31019 | -40031 |
| tool_errors | 0.7 / 1 | 1.7 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 2/3 | 2/3 |
| third-party-pins-match-pins-md | 2/3 | 2/3 |
| no-trailing-comments | 2/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
