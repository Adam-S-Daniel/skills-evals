# Eval report: workflow-path-audit

- Timestamp: 20261026T143657Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143656Z-43523e; started 2026-10-26T14:36:57Z, ended 2026-10-26T14:41:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.52 to 0.55, seven_day 0.77 to 0.77, from 8 snapshots

## Fixture: workflow-path-audit (n=3)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1436 / 0.4309 |
| without_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1177 / 0.3531 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1436 / 0.1338 | 0.1177 / 0.1108 | +0.0259 | +0.0230 |
| num_turns | 7.7 / 8 | 6 / 6 | +1.7 | +2 |
| duration_ms | 42267 / 42242 | 41134 / 42116 | +1133 | +126 |
| input_tokens | 12 / 12 | 11.3 / 12 | +0.7 | 0 |
| output_tokens | 3015.3 / 2997 | 3847.3 / 3605 | -832 | -608 |
| cache_creation_input_tokens | 22863.3 / 19333 | 15006.3 / 14534 | +7857 | +4799 |
| cache_read_input_tokens | 220152 / 225105 | 191924.3 / 203893 | +28227.7 | +21212 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 3/3 | 3/3 |
| source-change-routes-correctly | 3/3 | 2/3 |
| lockfile-change-routes-to-installers | 3/3 | 2/3 |
| prose-change-runs-nothing-but-the-required-check | 3/3 | 2/3 |
| required-check-always-fires-and-gates-internally | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 2/3 |
