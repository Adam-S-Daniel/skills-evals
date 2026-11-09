# Eval report: ci-job-performance

- Timestamp: 20261109T201938Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T201345Z-6a503a; started 2026-11-09T20:19:38Z, ended 2026-11-09T20:21:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.09, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 6 call(s); agent $0.36, judge $0.10, guard $0.00; last agent call $0.10

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/5 | 5.9 (5.4 to 7.0, 3 judged) | 0.1190 / 0.3570 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1190 / 0.1019 |
| num_turns | 6 / 6 |
| duration_ms | 21137.3 / 21051 |
| input_tokens | 12 / 12 |
| output_tokens | 2208.7 / 2254 |
| cache_creation_input_tokens | 29612 / 21851 |
| cache_read_input_tokens | 228467.7 / 238269 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| suite-is-not-sharded | 3/3 |
| installs-only-chromium | 3/3 |
| tests-not-pinned-to-one-worker | 3/3 |
| required-e2e-check-is-published | 3/3 |
| only-the-workflow-changed | 3/3 |
