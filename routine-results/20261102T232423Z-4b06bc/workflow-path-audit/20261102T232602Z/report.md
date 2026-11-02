# Eval report: workflow-path-audit

- Timestamp: 20261102T232602Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261102T232423Z-4b06bc; started 2026-11-02T23:26:02Z, ended 2026-11-02T23:27:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 4 call(s); agent $0.31, judge $0.17, guard $0.00; last agent call $0.12

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.9 (8.9 to 8.9, 1 judged) | 0.1846 / 0.1846 |
| without_skill | 1 | 0 | 8/8 | 8.7 (8.7 to 8.7, 1 judged) | 0.1222 / 0.1222 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1846 / 0.1846 | 0.1222 / 0.1222 | +0.0624 | +0.0624 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 34096 / 34096 | 31766 / 31766 | +2330 | +2330 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 3499 / 3499 | 3738 / 3738 | -239 | -239 |
| cache_creation_input_tokens | 30930 / 30930 | 15961 / 15961 | +14969 | +14969 |
| cache_read_input_tokens | 258386 / 258386 | 209501 / 209501 | +48885 | +48885 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-routes-correctly | 1/1 | 1/1 |
| source-change-routes-correctly | 1/1 | 1/1 |
| lockfile-change-routes-to-installers | 1/1 | 1/1 |
| prose-change-runs-nothing-but-the-required-check | 1/1 | 1/1 |
| required-check-always-fires-and-gates-internally | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
