# Eval report: workflow-path-audit

- Timestamp: 20261103T075013Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T074844Z-09fc9e; started 2026-11-03T07:50:13Z, ended 2026-11-03T07:51:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.28, judge $0.15, guard $0.00; last agent call $0.11

## Fixture: moved-test-dir (n=1)

- Prompt: Tighten the path filters on this repo's workflows: each one should run when, and only when, something it depends on changes.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 9.8 (9.8 to 9.8, 1 judged) | 0.1691 / 0.1691 |
| without_skill | 1 | 0 | 10/10 | 9.4 (9.4 to 9.4, 1 judged) | 0.1149 / 0.1149 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1691 / 0.1691 | 0.1149 / 0.1149 | +0.0542 | +0.0542 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 24795 / 24795 | 29961 / 29961 | -5166 | -5166 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 2135 / 2135 | 2644 / 2644 | -509 | -509 |
| cache_creation_input_tokens | 30472 / 30472 | 15903 / 15903 | +14569 | +14569 |
| cache_read_input_tokens | 258289 / 258289 | 248620 / 248620 | +9669 | +9669 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| moved-spec-runs-e2e | 1/1 | 1/1 |
| server-script-runs-e2e | 1/1 | 1/1 |
| own-workflow-edit-runs-itself | 1/1 | 1/1 |
| sibling-workflow-edit-runs-only-itself | 1/1 | 1/1 |
| unit-test-change-skips-e2e | 1/1 | 1/1 |
| prose-change-runs-nothing | 1/1 | 1/1 |
| lockfile-change-runs-every-installer | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
