# Eval report: workflow-path-audit

- Timestamp: 20261028T055102Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T055008Z-2e54ad; started 2026-10-28T05:51:02Z, ended 2026-10-28T05:52:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.03 to 0.04, seven_day 0.25 to 0.25, from 7 snapshots

## Fixture: required-check-routing (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/8 | 6.2 (5.4 to 7.7, 3 judged) | 0.1263 / 0.3788 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1263 / 0.0885 |
| num_turns | 6 / 6 |
| duration_ms | 22129.3 / 21919 |
| input_tokens | 12 / 12 |
| output_tokens | 1903 / 1908 |
| cache_creation_input_tokens | 21540.3 / 12138 |
| cache_read_input_tokens | 209282.3 / 218566 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| docs-change-routes-correctly | 3/3 |
| source-change-routes-correctly | 3/3 |
| lockfile-change-routes-to-installers | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 |
| required-check-always-fires-and-gates-internally | 0/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| ruleset-unchanged | 3/3 |
