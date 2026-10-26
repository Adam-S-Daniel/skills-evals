# Eval report: github-actions-sha-pinning

- Timestamp: 20261026T033745Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T033634Z-ae0399; started 2026-10-26T03:37:45Z, ended 2026-10-26T03:46:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.02 to 0.04, seven_day 0.54 to 0.54, from 8 snapshots

## Fixture: github-actions-sha-pinning (n=3)

- Prompt: Bring this repo's action pins into line with the pinning policy.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/10 | 9.1 (8.7 to 9.4, 3 judged) | 0.3415 / 1.0246 |
| without_skill | 3 | 0 | 9.3/10 | 9.2 (8.9 to 9.7, 3 judged) | 0.2851 / 0.8553 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3415 / 0.2603 | 0.2851 / 0.2769 | +0.0564 | -0.0167 |
| num_turns | 7 / 6 | 6.3 / 6 | +0.7 | 0 |
| duration_ms | 72537 / 63148 | 73824.7 / 74086 | -1287.7 | -10938 |
| input_tokens | 12.7 / 12 | 12.7 / 12 | 0 | 0 |
| output_tokens | 3851.3 / 3259 | 3984.3 / 3919 | -133 | -660 |
| cache_creation_input_tokens | 26163 / 18452 | 19066 / 18869 | +7097 | -417 |
| cache_read_input_tokens | 244360.7 / 221294 | 236228 / 222652 | +8132.7 | -1358 |
| tool_errors | 1.7 / 2 | 0.3 / 0 | +1.3 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| third-party-actions-sha-pinned | 2/3 | 2/3 |
| third-party-pins-match-pins-md | 2/3 | 2/3 |
| no-trailing-comments | 3/3 | 3/3 |
| cms-platform-refs-stay-on-tag | 3/3 | 3/3 |
| local-and-docker-refs-untouched | 3/3 | 3/3 |
| reference-files-untouched | 3/3 | 3/3 |
| ci-workflow-not-deleted | 3/3 | 3/3 |
| deploy-workflow-not-deleted | 3/3 | 3/3 |
| gate-action-not-deleted | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
