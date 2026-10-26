# Eval report: workflow-path-audit

- Timestamp: 20261026T060207Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T060039Z-5f4142; started 2026-10-26T06:02:07Z, ended 2026-10-26T06:07:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.56 to 0.56, from 7 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | 9.0 (8.9 to 9.2, 3 judged) | 0.1524 / 0.4572 |
| without_skill | 3 | 0 | 8/8 | 8.4 (8.1 to 8.9, 3 judged) | 0.1242 / 0.3727 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1524 / 0.1383 | 0.1242 / 0.1224 | +0.0282 | +0.0159 |
| num_turns | 7.7 / 8 | 5.7 / 6 | +2 | +2 |
| duration_ms | 32409.3 / 31704 | 41421 / 39495 | -9011.7 | -7791 |
| input_tokens | 13.3 / 14 | 11.3 / 12 | +2 | +2 |
| output_tokens | 3432.7 / 3298 | 4173.3 / 4058 | -740.7 | -760 |
| cache_creation_input_tokens | 23301 / 19799 | 15788.7 / 15314 | +7512.3 | +4485 |
| cache_read_input_tokens | 248511.7 / 256930 | 193388.7 / 205496 | +55123 | +51434 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 3/3 |
| lockfile-change-routes-to-installers | 3/3 | 3/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 3/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
