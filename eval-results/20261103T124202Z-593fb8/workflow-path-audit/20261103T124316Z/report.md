# Eval report: workflow-path-audit

- Timestamp: 20261103T124316Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T124202Z-593fb8; started 2026-11-03T12:43:16Z, ended 2026-11-03T12:47:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.41, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.60 over 4 call(s); agent $0.90, judge $0.71, guard $0.00; last agent call $0.47

## Fixture: moved-test-dir (n=1)

- Prompt: Tighten the path filters on this repo's workflows: each one should run when, and only when, something it depends on changes.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 9.2 (9.2 to 9.2, 1 judged) | 0.4303 / 0.4303 |
| without_skill | 1 | 0 | 10/10 | 7.8 (7.8 to 7.8, 1 judged) | 0.4659 / 0.4659 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4303 / 0.4303 | 0.4659 / 0.4659 | -0.0357 | -0.0357 |
| num_turns | 8 / 8 | 11 / 11 | -3 | -3 |
| duration_ms | 75464 / 75464 | 108421 / 108421 | -32957 | -32957 |
| input_tokens | 18 / 18 | 24 / 24 | -6 | -6 |
| output_tokens | 3791 / 3791 | 7422 / 7422 | -3631 | -3631 |
| cache_creation_input_tokens | 36781 / 36781 | 27072 / 27072 | +9709 | +9709 |
| cache_read_input_tokens | 274569 / 274569 | 468915 / 468915 | -194346 | -194346 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
