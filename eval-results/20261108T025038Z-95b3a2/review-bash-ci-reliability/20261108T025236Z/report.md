# Eval report: review-bash-ci-reliability

- Timestamp: 20261108T025236Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T025038Z-95b3a2; started 2026-11-08T02:52:36Z, ended 2026-11-08T02:53:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: pages-temp-repo-commit (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1374 / 0.1374 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.0906 / 0.0906 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1374 / 0.1374 | 0.0906 / 0.0906 | +0.0468 | +0.0468 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 23507 / 23507 | 26102 / 26102 | -2595 | -2595 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2101 / 2101 | 2198 / 2198 | -97 | -97 |
| cache_creation_input_tokens | 25928 / 25928 | 12944 / 12944 | +12984 | +12984 |
| cache_read_input_tokens | 126793 / 126793 | 168000 / 168000 | -41207 | -41207 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| fresh-runner | 1/1 | 1/1 |
| signing-on-runner | 1/1 | 0/1 |
| developer-config-untouched | 1/1 | 1/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| docs-untouched | 1/1 | 1/1 |
