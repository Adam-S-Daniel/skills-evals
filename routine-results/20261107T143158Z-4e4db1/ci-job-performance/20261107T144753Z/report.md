# Eval report: ci-job-performance

- Timestamp: 20261107T144753Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143158Z-4e4db1; started 2026-11-07T14:47:53Z, ended 2026-11-07T14:57:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.47, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 12 call(s); agent $0.91, judge $0.26, guard $0.00; last agent call $0.13

## Fixture: spawn-per-test (n=3)

- Prompt: `lint-tests` is the slowest required check in this private repository: its "Run the tests" step took 38s, 44s and 41s on the last three pull requests, and the rest of the job takes about 12s. A teammate suggests switching to pytest-xdist with `-n 8`, or splitting the tests across a four-job matrix. Make the check faster, without dropping or weakening any test, and tell us what you measured.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | 8.8 (8.6 to 9.0, 3 judged) | 0.1568 / 0.4704 |
| without_skill | 3 | 0 | 6/6 | 8.5 (8.0 to 8.8, 3 judged) | 0.1475 / 0.4424 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1568 / 0.1543 | 0.1475 / 0.1326 | +0.0093 | +0.0217 |
| num_turns | 10.3 / 11 | 11 / 10 | -0.7 | +1 |
| duration_ms | 73186.7 / 73120 | 86519 / 93312 | -13332.3 | -20192 |
| input_tokens | 18 / 20 | 19.3 / 18 | -1.3 | +2 |
| output_tokens | 3318.3 / 3531 | 4058.3 / 3533 | -740 | -2 |
| cache_creation_input_tokens | 23236 / 20214 | 17613 / 16955 | +5623 | +3259 |
| cache_read_input_tokens | 306370.7 / 341300 | 364058 / 328283 | -57687.3 | +13017 |
| tool_errors | 0.7 / 0 | 1 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-passes-with-every-test | 3/3 | 3/3 |
| linter-started-at-most-once-per-page | 3/3 | 3/3 |
| tests-still-catch-a-broken-rule | 3/3 | 3/3 |
| required-check-still-runs-the-suite | 3/3 | 3/3 |
| no-oversubscribed-workers | 3/3 | 3/3 |
| linter-and-pages-unchanged | 3/3 | 3/3 |
