# Eval report: ci-job-performance

- Timestamp: 20261107T143503Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T142820Z-6c7d09; started 2026-11-07T14:35:03Z, ended 2026-11-07T14:36:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.46, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 6 call(s); agent $0.50, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: sharded-required-check (n=3)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/5 | skipped (objective-decided) | 0.0971 / 0.2912 |
| without_skill | 3 | 0 | 3/5 | skipped (objective-decided) | 0.0693 / 0.2080 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0971 / 0.0892 | 0.0693 / 0.0694 | +0.0278 | +0.0199 |
| num_turns | 4.3 / 5 | 3 / 3 | +1.3 | +2 |
| duration_ms | 17480.3 / 15327 | 14323.3 / 14355 | +3157 | +972 |
| input_tokens | 7.3 / 8 | 6 / 6 | +1.3 | +2 |
| output_tokens | 1621.3 / 1668 | 1420.7 / 1414 | +200.7 | +254 |
| cache_creation_input_tokens | 17824.7 / 15483 | 11373.7 / 11397 | +6451 | +4086 |
| cache_read_input_tokens | 95515.3 / 100369 | 96128.7 / 96145 | -613.3 | +4224 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 3/3 | 3/3 |
| required-e2e-check-is-published-by-a-gate | 1/3 | 3/3 |
| gate-cannot-be-cancelled | 2/3 | 0/3 |
| no-matrix-value-in-a-run-body | 2/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
