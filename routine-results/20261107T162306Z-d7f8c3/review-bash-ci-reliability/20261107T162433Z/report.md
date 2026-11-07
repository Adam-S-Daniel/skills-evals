# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T162433Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T162306Z-d7f8c3; started 2026-11-07T16:24:33Z, ended 2026-11-07T16:38:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.55, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.99 over 12 call(s); agent $3.01, judge $0.98, guard $0.00; last agent call $0.50

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/8 | 8.7 (8.2 to 9.4, 3 judged) | 0.4986 / 1.4959 |
| without_skill | 3 | 0 | 4/8 | 4.8 (4.7 to 5.0, 3 judged) | 0.5035 / 1.5104 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4986 / 0.5040 | 0.5035 / 0.5025 | -0.0048 | +0.0015 |
| num_turns | 8.7 / 8 | 7.3 / 7 | +1.3 | +1 |
| duration_ms | 111211 / 110735 | 124302 / 123977 | -13091 | -13242 |
| input_tokens | 17.3 / 16 | 16 / 16 | +1.3 | 0 |
| output_tokens | 7479.7 / 7846 | 7459 / 7645 | +20.7 | +201 |
| cache_creation_input_tokens | 27921 / 24751 | 22698.7 / 23234 | +5222.3 | +1517 |
| cache_read_input_tokens | 250295 / 223088 | 258896.7 / 259618 | -8601.7 | -36530 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| signing-on-runner | 0/3 | 0/3 |
| no-change-night | 0/3 | 0/3 |
| missing-tool-not-silent | 0/3 | 0/3 |
| new-data-still-committed | 0/3 | 0/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| data-untouched | 3/3 | 3/3 |
