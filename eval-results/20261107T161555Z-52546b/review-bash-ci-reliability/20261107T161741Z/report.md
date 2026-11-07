# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T161741Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161555Z-52546b; started 2026-11-07T16:17:41Z, ended 2026-11-07T16:29:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.54, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.03 over 6 call(s); agent $3.03, judge $0.00, guard $0.00; last agent call $0.44

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.5615 / 1.6845 |
| without_skill | 3 | 0 | 4.3/7 | skipped (objective-decided) | 0.4495 / 1.3484 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5615 / 0.5578 | 0.4495 / 0.4378 | +0.1120 | +0.1200 |
| num_turns | 9.7 / 9 | 6.7 / 7 | +3 | +2 |
| duration_ms | 132781.3 / 113281 | 98415.7 / 97045 | +34365.7 | +16236 |
| input_tokens | 22 / 20 | 15.3 / 16 | +6.7 | +4 |
| output_tokens | 7032.7 / 5844 | 5953.3 / 5505 | +1079.3 | +339 |
| cache_creation_input_tokens | 28612.7 / 30389 | 20517.7 / 20201 | +8095 | +10188 |
| cache_read_input_tokens | 335349 / 289946 | 240747.7 / 253811 | +94601.3 | +36135 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| every-drifted-file-reported | 2/3 | 1/3 |
| unowned-template-not-fatal | 2/3 | 1/3 |
| clean-tree-still-passes | 3/3 | 1/3 |
| drift-and-missing-still-fail | 3/3 | 1/3 |
| config-data-untouched | 3/3 | 3/3 |
