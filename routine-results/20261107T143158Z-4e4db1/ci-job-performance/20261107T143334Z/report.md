# Eval report: ci-job-performance

- Timestamp: 20261107T143334Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T143158Z-4e4db1; started 2026-11-07T14:33:34Z, ended 2026-11-07T14:47:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.46, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.96 over 6 call(s); agent $2.96, judge $0.00, guard $0.00; last agent call $0.38

## Fixture: spawn-per-test (n=3)

- Prompt: `lint-tests` is the slowest required check in this private repository: its "Run the tests" step took 38s, 44s and 41s on the last three pull requests, and the rest of the job takes about 12s. A teammate suggests switching to pytest-xdist with `-n 8`, or splitting the tests across a four-job matrix. Make the check faster, without dropping or weakening any test, and tell us what you measured.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/6 | skipped (objective-decided) | 0.5088 / 1.5263 |
| without_skill | 3 | 0 | 5.3/6 | skipped (objective-decided) | 0.4769 / 1.4307 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5088 / 0.5156 | 0.4769 / 0.5113 | +0.0319 | +0.0043 |
| num_turns | 13.7 / 14 | 10.7 / 12 | +3 | +2 |
| duration_ms | 138889.3 / 129100 | 124888 / 134542 | +14001.3 | -5442 |
| input_tokens | 27.3 / 28 | 23.3 / 26 | +4 | +2 |
| output_tokens | 6129.3 / 5822 | 6373.7 / 7047 | -244.3 | -1225 |
| cache_creation_input_tokens | 34206.7 / 33988 | 30684 / 31547 | +3522.7 | +2441 |
| cache_read_input_tokens | 530479 / 541215 | 488110.7 / 559869 | +42368.3 | -18654 |
| tool_errors | 2.3 / 2 | 1 / 1 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-passes-with-every-test | 3/3 | 3/3 |
| linter-started-at-most-once-per-page | 2/3 | 1/3 |
| tests-still-catch-a-broken-rule | 3/3 | 3/3 |
| required-check-still-runs-the-suite | 3/3 | 3/3 |
| no-oversubscribed-workers | 3/3 | 3/3 |
| linter-and-pages-unchanged | 3/3 | 3/3 |
