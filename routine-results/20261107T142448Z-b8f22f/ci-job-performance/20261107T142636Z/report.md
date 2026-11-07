# Eval report: ci-job-performance

- Timestamp: 20261107T142636Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T142448Z-b8f22f; started 2026-11-07T14:26:36Z, ended 2026-11-07T14:37:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.45 to 0.46, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.77 over 12 call(s); agent $2.95, judge $0.82, guard $0.00; last agent call $0.44

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 7.8 (6.4 to 9.0, 3 judged) | 0.5401 / 1.6204 |
| without_skill | 3 | 0 | 4.7/5 | 8.1 (7.0 to 9.2, 3 judged) | 0.4431 / 1.3293 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5401 / 0.5646 | 0.4431 / 0.4420 | +0.0970 | +0.1226 |
| num_turns | 13.3 / 13 | 9 / 9 | +4.3 | +4 |
| duration_ms | 95054.7 / 95484 | 78993 / 81789 | +16061.7 | +13695 |
| input_tokens | 26.7 / 28 | 18 / 20 | +8.7 | +8 |
| output_tokens | 6067.3 / 5713 | 4952.7 / 4871 | +1114.7 | +842 |
| cache_creation_input_tokens | 38050 / 40756 | 33196 / 33858 | +4854 | +6898 |
| cache_read_input_tokens | 553471 / 530534 | 367953.7 / 393310 | +185517.3 | +137224 |
| tool_errors | 0.7 / 0 | 0.3 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-not-sharded | 3/3 | 3/3 |
| installs-only-chromium | 2/3 | 3/3 |
| tests-not-pinned-to-one-worker | 2/3 | 3/3 |
| required-e2e-check-is-published | 3/3 | 3/3 |
| only-the-workflow-changed | 2/3 | 2/3 |
