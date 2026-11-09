# Eval report: ci-job-performance

- Timestamp: 20261109T201647Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T201345Z-6a503a; started 2026-11-09T20:16:47Z, ended 2026-11-09T20:19:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.26 over 6 call(s); agent $1.01, judge $0.25, guard $0.00; last agent call $0.27

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/5 | 8.2 (8.0 to 8.6, 3 judged) | 0.3369 / 1.0108 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3369 / 0.2806 |
| num_turns | 8 / 8 |
| duration_ms | 42433.7 / 39070 |
| input_tokens | 16 / 16 |
| output_tokens | 3750.7 / 3515 |
| cache_creation_input_tokens | 38572.7 / 28618 |
| cache_read_input_tokens | 344913.7 / 354563 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| suite-is-not-sharded | 3/3 |
| installs-only-chromium | 3/3 |
| tests-not-pinned-to-one-worker | 3/3 |
| required-e2e-check-is-published | 3/3 |
| only-the-workflow-changed | 3/3 |
