# Eval report: workflow-path-audit

- Timestamp: 20261103T124521Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T124306Z-892f4f; started 2026-11-03T12:45:21Z, ended 2026-11-03T12:50:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.41, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.06 over 4 call(s); agent $1.18, judge $0.88, guard $0.00; last agent call $0.55

## Fixture: required-check-routing (n=1)

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 8.9 (8.9 to 8.9, 1 judged) | 0.6329 / 0.6329 |
| without_skill | 1 | 0 | 8/8 | 9.6 (9.6 to 9.6, 1 judged) | 0.5511 / 0.5511 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6329 / 0.6329 | 0.5511 / 0.5511 | +0.0818 | +0.0818 |
| num_turns | 12 / 12 | 12 / 12 | 0 | 0 |
| duration_ms | 118525 / 118525 | 137160 / 137160 | -18635 | -18635 |
| input_tokens | 26 / 26 | 26 / 26 | 0 | 0 |
| output_tokens | 9568 / 9568 | 10962 / 10962 | -1394 | -1394 |
| cache_creation_input_tokens | 41888 / 41888 | 27727 / 27727 | +14161 | +14161 |
| cache_read_input_tokens | 496797 / 496797 | 514571 / 514571 | -17774 | -17774 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
