# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T150624Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T150454Z-da8a34; started 2026-10-26T15:06:24Z, ended 2026-10-26T15:08:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.76 to 0.78, seven_day 0.82 to 0.82, from 7 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/10 | skipped (objective-decided) | 0.0980 / 0.2941 |
| without_skill | 3 | 0 | 8.7/10 | skipped (objective-decided) | 0.0832 / 0.2495 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0980 / 0.0852 | 0.0832 / 0.0831 | +0.0149 | +0.0021 |
| num_turns | 4 / 4 | 4 / 4 | 0 | 0 |
| duration_ms | 18365.7 / 18923 | 16243.7 / 16068 | +2122 | +2855 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 1316 / 1334 | 1336.3 / 1329 | -20.3 | +5 |
| cache_creation_input_tokens | 17842.3 / 14504 | 14001.7 / 13898 | +3840.7 | +606 |
| cache_read_input_tokens | 135039 / 138351 | 137877.7 / 137921 | -2838.7 | +430 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
