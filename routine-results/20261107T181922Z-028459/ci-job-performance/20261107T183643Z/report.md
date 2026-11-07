# Eval report: ci-job-performance

- Timestamp: 20261107T183643Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181922Z-028459; started 2026-11-07T18:36:43Z, ended 2026-11-07T18:46:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.17 over 12 call(s); agent $0.91, judge $0.26, guard $0.00; last agent call $0.14

## Fixture: spawn-per-test (n=3)

- Prompt: `lint-tests` is the slowest required check in this private repository: its "Run the tests" step took 38s, 44s and 41s on the last three pull requests, and the rest of the job takes about 12s. A teammate suggests switching to pytest-xdist with `-n 8`, or splitting the tests across a four-job matrix. Make the check faster, without dropping or weakening any test, and tell us what you measured.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | 8.8 (8.8 to 8.8, 3 judged) | 0.1694 / 0.5082 |
| without_skill | 3 | 0 | 6/6 | 8.7 (8.6 to 8.8, 3 judged) | 0.1349 / 0.4048 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1694 / 0.1630 | 0.1349 / 0.1360 | +0.0345 | +0.0270 |
| num_turns | 11.3 / 11 | 9 / 9 | +2.3 | +2 |
| duration_ms | 105958.3 / 75998 | 72933 / 75307 | +33025.3 | +691 |
| input_tokens | 21.3 / 22 | 16 / 16 | +5.3 | +6 |
| output_tokens | 3580.3 / 3672 | 3598.7 / 3676 | -18.3 | -4 |
| cache_creation_input_tokens | 23937 / 20518 | 17362.3 / 17621 | +6574.7 | +2897 |
| cache_read_input_tokens | 378158.7 / 383591 | 294765.7 / 295843 | +83393 | +87748 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-passes-with-every-test | 3/3 | 3/3 |
| linter-started-at-most-once-per-page | 3/3 | 3/3 |
| tests-still-catch-a-broken-rule | 3/3 | 3/3 |
| required-check-still-runs-the-suite | 3/3 | 3/3 |
| no-oversubscribed-workers | 3/3 | 3/3 |
| linter-and-pages-unchanged | 3/3 | 3/3 |
