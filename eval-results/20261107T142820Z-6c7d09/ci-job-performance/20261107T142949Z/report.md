# Eval report: ci-job-performance

- Timestamp: 20261107T142949Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T142820Z-6c7d09; started 2026-11-07T14:29:49Z, ended 2026-11-07T14:35:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.45, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.58 over 6 call(s); agent $1.58, judge $0.00, guard $0.00; last agent call $0.19

## Fixture: sharded-required-check (n=3)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/5 | skipped (objective-decided) | 0.3018 / 0.9054 |
| without_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.2256 / 0.6768 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3018 / 0.2865 | 0.2256 / 0.2183 | +0.0762 | +0.0682 |
| num_turns | 7.3 / 7 | 5.7 / 5 | +1.7 | +2 |
| duration_ms | 50368.3 / 48944 | 49613.7 / 49390 | +754.7 | -446 |
| input_tokens | 13.3 / 14 | 12.7 / 12 | +0.7 | +2 |
| output_tokens | 3820 / 3909 | 3275.3 / 3125 | +544.7 | +784 |
| cache_creation_input_tokens | 23070.7 / 19710 | 14628 / 14576 | +8442.7 | +5134 |
| cache_read_input_tokens | 195834.7 / 186441 | 199528 / 172751 | -3693.3 | +13690 |
| tool_errors | 1.7 / 2 | 0.7 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 2/3 | 3/3 |
| required-e2e-check-is-published-by-a-gate | 2/3 | 3/3 |
| gate-cannot-be-cancelled | 3/3 | 0/3 |
| no-matrix-value-in-a-run-body | 3/3 | 3/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
