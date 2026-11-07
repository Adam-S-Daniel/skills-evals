# Eval report: ci-job-performance

- Timestamp: 20261107T180350Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180151Z-367c4a; started 2026-11-07T18:03:50Z, ended 2026-11-07T18:11:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.52 over 12 call(s); agent $1.68, judge $0.83, guard $0.00; last agent call $0.21

## Fixture: sharded-required-check (n=3)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.3/5 | 8.9 (8.8 to 9.0, 3 judged) | 0.3251 / 0.9754 |
| without_skill | 3 | 0 | 4/5 | 7.0 (5.8 to 8.2, 3 judged) | 0.2354 / 0.7061 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3251 / 0.3047 | 0.2354 / 0.2315 | +0.0898 | +0.0732 |
| num_turns | 8.3 / 8 | 5.3 / 5 | +3 | +3 |
| duration_ms | 64531.3 / 67221 | 54616.3 / 55378 | +9915 | +11843 |
| input_tokens | 16.7 / 16 | 12 / 12 | +4.7 | +4 |
| output_tokens | 4172 / 4216 | 3758.3 / 3648 | +413.7 | +568 |
| cache_creation_input_tokens | 23556.3 / 20463 | 15005.3 / 14912 | +8551 | +5551 |
| cache_read_input_tokens | 240412.3 / 230240 | 185200.3 / 173494 | +55212 | +56746 |
| tool_errors | 1.7 / 2 | 1 / 1 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 1/3 | 3/3 |
| required-e2e-check-is-published-by-a-gate | 0/3 | 3/3 |
| gate-cannot-be-cancelled | 3/3 | 0/3 |
| no-matrix-value-in-a-run-body | 3/3 | 3/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
