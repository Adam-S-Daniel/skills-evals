# Eval report: ci-job-performance

- Timestamp: 20261107T182055Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181922Z-028459; started 2026-11-07T18:20:55Z, ended 2026-11-07T18:36:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.6, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.57 over 12 call(s); agent $2.87, judge $0.71, guard $0.00; last agent call $0.49

## Fixture: spawn-per-test (n=3)

- Prompt: `lint-tests` is the slowest required check in this private repository: its "Run the tests" step took 38s, 44s and 41s on the last three pull requests, and the rest of the job takes about 12s. A teammate suggests switching to pytest-xdist with `-n 8`, or splitting the tests across a four-job matrix. Make the check faster, without dropping or weakening any test, and tell us what you measured.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/6 | 8.9 (8.4 to 9.2, 3 judged) | 0.5052 / 1.5157 |
| without_skill | 3 | 0 | 5.7/6 | 7.3 (4.4 to 8.8, 3 judged) | 0.4499 / 1.3497 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5052 / 0.5264 | 0.4499 / 0.4779 | +0.0553 | +0.0485 |
| num_turns | 12 / 12 | 11 / 12 | +1 | 0 |
| duration_ms | 133225.7 / 130148 | 132151.7 / 153388 | +1074 | -23240 |
| input_tokens | 25.3 / 26 | 23.3 / 26 | +2 | 0 |
| output_tokens | 5826.7 / 5858 | 5603 / 5945 | +223.7 | -87 |
| cache_creation_input_tokens | 35593 / 34518 | 29290.7 / 30518 | +6302.3 | +4000 |
| cache_read_input_tokens | 487979.3 / 461874 | 494878 / 545133 | -6898.7 | -83259 |
| tool_errors | 1.3 / 2 | 0.7 / 1 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-passes-with-every-test | 3/3 | 3/3 |
| linter-started-at-most-once-per-page | 2/3 | 2/3 |
| tests-still-catch-a-broken-rule | 3/3 | 3/3 |
| required-check-still-runs-the-suite | 3/3 | 3/3 |
| no-oversubscribed-workers | 3/3 | 3/3 |
| linter-and-pages-unchanged | 3/3 | 3/3 |
