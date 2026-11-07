# Eval report: ci-job-performance

- Timestamp: 20261107T181721Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181548Z-4384b3; started 2026-11-07T18:17:21Z, ended 2026-11-07T18:27:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.6, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.72 over 12 call(s); agent $2.96, judge $0.76, guard $0.00; last agent call $0.38

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/5 | 8.3 (8.2 to 8.4, 3 judged) | 0.5460 / 1.6380 |
| without_skill | 3 | 0 | 5/5 | 8.3 (7.8 to 9.0, 3 judged) | 0.4397 / 1.3192 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5460 / 0.5432 | 0.4397 / 0.4652 | +0.1063 | +0.0780 |
| num_turns | 11.3 / 11 | 8.3 / 8 | +3 | +3 |
| duration_ms | 96889.7 / 95995 | 71928 / 75520 | +24961.7 | +20475 |
| input_tokens | 24 / 24 | 17.3 / 18 | +6.7 | +6 |
| output_tokens | 6504.3 / 6609 | 4554 / 4512 | +1950.3 | +2097 |
| cache_creation_input_tokens | 40112.7 / 39829 | 34091 / 34036 | +6021.7 | +5793 |
| cache_read_input_tokens | 452253.7 / 434216 | 357000.3 / 332048 | +95253.3 | +102168 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-not-sharded | 3/3 | 3/3 |
| installs-only-chromium | 3/3 | 3/3 |
| tests-not-pinned-to-one-worker | 3/3 | 3/3 |
| required-e2e-check-is-published | 3/3 | 3/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
