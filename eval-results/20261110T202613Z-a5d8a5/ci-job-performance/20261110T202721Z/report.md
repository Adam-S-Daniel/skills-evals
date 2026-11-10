# Eval report: ci-job-performance

- Timestamp: 20261110T202721Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T202613Z-a5d8a5; started 2026-11-10T20:27:21Z, ended 2026-11-10T20:29:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.28, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 6 call(s); agent $0.52, judge $0.24, guard $0.00; last agent call $0.13

## Fixture: sharded-required-check (n=3)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3/5 | 5.6 (5.4 to 5.8, 3 judged) | 0.1738 / 0.5214 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1738 / 0.1316 |
| num_turns | 5 / 5 |
| duration_ms | 21561 / 21502 |
| input_tokens | 10 / 10 |
| output_tokens | 1936.7 / 1925 |
| cache_creation_input_tokens | 20163 / 10827 |
| cache_read_input_tokens | 171096.3 / 180509 |
| tool_errors | 1.3 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 3/3 |
| required-e2e-check-is-published-by-a-gate | 3/3 |
| gate-cannot-be-cancelled | 0/3 |
| no-matrix-value-in-a-run-body | 0/3 |
| only-the-workflow-changed | 3/3 |
