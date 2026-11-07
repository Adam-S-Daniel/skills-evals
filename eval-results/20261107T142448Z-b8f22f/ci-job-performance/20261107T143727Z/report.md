# Eval report: ci-job-performance

- Timestamp: 20261107T143727Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T142448Z-b8f22f; started 2026-11-07T14:37:27Z, ended 2026-11-07T14:41:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.46, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.91, judge $0.00, guard $0.00; last agent call $0.16

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/5 | skipped (objective-decided) | 0.1618 / 0.4854 |
| without_skill | 3 | 0 | 4.7/5 | skipped (objective-decided) | 0.1412 / 0.4237 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1618 / 0.1530 | 0.1412 / 0.1399 | +0.0206 | +0.0130 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 42873 / 34345 | 31084 / 34131 | +11789 | +214 |
| input_tokens | 16 / 16 | 11.3 / 12 | +4.7 | +4 |
| output_tokens | 2569.3 / 2620 | 2098 / 2207 | +471.3 | +413 |
| cache_creation_input_tokens | 27040.7 / 23976 | 24529 / 23680 | +2511.7 | +296 |
| cache_read_input_tokens | 279072.7 / 283800 | 221029.7 / 231143 | +58043 | +52657 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-not-sharded | 3/3 | 3/3 |
| installs-only-chromium | 3/3 | 3/3 |
| tests-not-pinned-to-one-worker | 3/3 | 2/3 |
| required-e2e-check-is-published | 3/3 | 3/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
