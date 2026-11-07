# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T181019Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180840Z-06df9d; started 2026-11-07T18:10:19Z, ended 2026-11-07T18:24:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.6, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.70 over 6 call(s); agent $3.70, judge $0.00, guard $0.00; last agent call $0.77

## Fixture: pages-temp-repo-commit (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.5514 / 1.6542 |
| without_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.6804 / 2.0412 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5514 / 0.5596 | 0.6804 / 0.6423 | -0.1290 | -0.0827 |
| num_turns | 9.7 / 10 | 10.3 / 11 | -0.7 | -1 |
| duration_ms | 115696.3 / 106946 | 163845.7 / 165138 | -48149.3 | -58192 |
| input_tokens | 20 / 20 | 22.7 / 24 | -2.7 | -4 |
| output_tokens | 6651.7 / 6905 | 9674 / 10104 | -3022.3 | -3199 |
| cache_creation_input_tokens | 27464 / 24890 | 30128 / 28373 | -2664 | -3483 |
| cache_read_input_tokens | 309615.7 / 307364 | 409971.3 / 453287 | -100355.7 | -145923 |
| tool_errors | 1.3 / 1 | 1.3 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| fresh-runner | 3/3 | 3/3 |
| signing-on-runner | 3/3 | 1/3 |
| developer-config-untouched | 3/3 | 3/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| docs-untouched | 3/3 | 3/3 |
