# Eval report: workflow-path-audit

- Timestamp: 20261026T143434Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143433Z-3ea5e8; started 2026-10-26T14:34:34Z, ended 2026-10-26T14:41:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.5 to 0.54, seven_day 0.76 to 0.77, from 9 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | 8.9 (8.9 to 8.9, 3 judged) | 0.1444 / 0.4331 |
| without_skill | 3 | 0 | 8/8 | 8.7 (8.2 to 8.9, 3 judged) | 0.1192 / 0.3575 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1444 / 0.1394 | 0.1192 / 0.1202 | +0.0252 | +0.0191 |
| num_turns | 7.7 / 8 | 7 / 7 | +0.7 | +1 |
| duration_ms | 45168 / 45713 | 51991.3 / 47324 | -6823.3 | -1611 |
| input_tokens | 11.3 / 12 | 14 / 14 | -2.7 | -2 |
| output_tokens | 3161 / 3277 | 3495.3 / 3479 | -334.3 | -202 |
| cache_creation_input_tokens | 23001.7 / 20578 | 14980.7 / 14943 | +8021 | +5635 |
| cache_read_input_tokens | 207149.3 / 224870 | 242614.7 / 242934 | -35465.3 | -18064 |
| tool_errors | 0.7 / 0 | 0 / 0 | +0.7 | 0 |

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
