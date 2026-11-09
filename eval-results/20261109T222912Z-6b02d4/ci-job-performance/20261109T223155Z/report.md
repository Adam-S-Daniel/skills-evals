# Eval report: ci-job-performance

- Timestamp: 20261109T223155Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T222912Z-6b02d4; started 2026-11-09T22:31:55Z, ended 2026-11-09T22:42:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.36 over 6 call(s); agent $1.12, judge $0.23, guard $0.00; last agent call $0.38

## Fixture: spawn-per-test (n=3)

- Prompt: `lint-tests` is the slowest required check in this private repository: its "Run the tests" step took 38s, 44s and 41s on the last three pull requests, and the rest of the job takes about 12s. A teammate suggests switching to pytest-xdist with `-n 8`, or splitting the tests across a four-job matrix. Make the check faster, without dropping or weakening any test, and tell us what you measured.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6/6 | 8.7 (8.6 to 8.8, 3 judged) | 0.3746 / 1.1238 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3746 / 0.3753 |
| num_turns | 9 / 9 |
| duration_ms | 191706.3 / 192998 |
| input_tokens | 18 / 18 |
| output_tokens | 5647.3 / 5582 |
| cache_creation_input_tokens | 36196.7 / 28590 |
| cache_read_input_tokens | 403040 / 408987 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| suite-passes-with-every-test | 3/3 |
| linter-started-at-most-once-per-page | 3/3 |
| tests-still-catch-a-broken-rule | 3/3 |
| required-check-still-runs-the-suite | 3/3 |
| no-oversubscribed-workers | 3/3 |
| linter-and-pages-unchanged | 3/3 |
