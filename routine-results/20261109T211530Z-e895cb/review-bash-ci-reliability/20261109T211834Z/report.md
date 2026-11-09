# Eval report: review-bash-ci-reliability

- Timestamp: 20261109T211834Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T211530Z-e895cb; started 2026-11-09T21:18:34Z, ended 2026-11-09T21:20:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 6 call(s); agent $0.26, judge $0.10, guard $0.00; last agent call $0.06

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6/7 | 5.2 (5.1 to 5.3, 3 judged) | 0.0873 / 0.2618 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0873 / 0.0710 |
| num_turns | 4.7 / 4 |
| duration_ms | 19007.3 / 17982 |
| input_tokens | 9.3 / 8 |
| output_tokens | 2106.7 / 2123 |
| cache_creation_input_tokens | 20220.7 / 10958 |
| cache_read_input_tokens | 156369.3 / 139952 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| fresh-runner | 3/3 |
| signing-on-runner | 0/3 |
| developer-config-untouched | 3/3 |
| build-failure-still-fails | 3/3 |
| docs-untouched | 3/3 |
