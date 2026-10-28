# Eval report: workflow-path-audit

- Timestamp: 20261028T065443Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T065351Z-3e5794; started 2026-10-28T06:54:43Z, ended 2026-10-28T06:59:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.05 to 0.06, seven_day 0.26 to 0.26, from 9 snapshots

## Fixture: required-check-routing (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.7/8 | 8.4 (6.9 to 9.5, 3 judged) | 0.3114 / 0.9341 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3114 / 0.2318 |
| num_turns | 4.7 / 5 |
| duration_ms | 53382 / 54864 |
| input_tokens | 9.3 / 10 |
| output_tokens | 3908 / 3747 |
| cache_creation_input_tokens | 25028.7 / 14913 |
| cache_read_input_tokens | 164088.3 / 161929 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| docs-change-routes-correctly | 3/3 |
| source-change-routes-correctly | 3/3 |
| lockfile-change-routes-to-installers | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 |
| required-check-always-fires-and-gates-internally | 2/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| ruleset-unchanged | 3/3 |
