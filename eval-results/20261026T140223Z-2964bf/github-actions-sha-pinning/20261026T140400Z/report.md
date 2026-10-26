# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T140400Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140223Z-2964bf; started 2026-10-26T14:04:00Z, ended 2026-10-26T14:11:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.26 to 0.34, seven_day 0.71 to 0.72, from 11 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | skipped (objective-decided) | 0.3192 / 0.9575 |
| without_skill | 3 | 0 | 9.3/10 | skipped (objective-decided) | 0.2711 / 0.8134 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3192 / 0.2792 | 0.2711 / 0.2692 | +0.0480 | +0.0101 |
| num_turns | 6.7 / 6 | 6.7 / 6 | 0 | 0 |
| duration_ms | 72942.7 / 77535 | 69339 / 57826 | +3603.7 | +19709 |
| input_tokens | 13.3 / 12 | 13.3 / 12 | 0 | 0 |
| output_tokens | 4110.7 / 3905 | 3565.7 / 3406 | +545 | +499 |
| cache_creation_input_tokens | 22737.3 / 18931 | 18304.3 / 18912 | +4433 | +19 |
| cache_read_input_tokens | 246536.7 / 221804 | 249518.7 / 222867 | -2982 | -1063 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 3/3 | 2/3 |
| third-party-pins-match-pins-md | 3/3 | 2/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
