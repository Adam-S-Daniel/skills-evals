# Eval report: ci-job-performance

- Timestamp: 20261107T221312Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T221131Z-3aee71; started 2026-11-07T22:13:12Z, ended 2026-11-07T22:14:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.69, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 2 call(s); agent $0.21, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: sharded-required-check (n=1)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1315 / 0.1315 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.0741 / 0.0741 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1315 / 0.1315 | 0.0741 / 0.0741 | +0.0574 | +0.0574 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 19907 / 19907 | 23671 / 23671 | -3764 | -3764 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 1704 / 1704 | 1470 / 1470 | +234 | +234 |
| cache_creation_input_tokens | 26369 / 26369 | 11546 / 11546 | +14823 | +14823 |
| cache_read_input_tokens | 89571 / 89571 | 131981 / 131981 | -42410 | -42410 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 1/1 | 1/1 |
| required-e2e-check-is-published-by-a-gate | 0/1 | 1/1 |
| gate-cannot-be-cancelled | 1/1 | 0/1 |
| no-matrix-value-in-a-run-body | 1/1 | 0/1 |
| only-the-workflow-changed | 1/1 | 1/1 |
