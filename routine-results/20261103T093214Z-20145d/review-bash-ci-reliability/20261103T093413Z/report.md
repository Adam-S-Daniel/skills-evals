# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T093413Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T093214Z-20145d; started 2026-11-03T09:34:13Z, ended 2026-11-03T09:38:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.72 over 4 call(s); agent $1.16, judge $0.56, guard $0.00; last agent call $0.46

## Fixture: empty-repo-discovery (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.9 (8.9 to 8.9, 1 judged) | 0.6952 / 0.6952 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.4609 / 0.4609 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6952 / 0.6952 | 0.4609 / 0.4609 | +0.2343 | +0.2343 |
| num_turns | 9 / 9 | 8 / 8 | +1 | +1 |
| duration_ms | 103372 / 103372 | 97426 / 97426 | +5946 | +5946 |
| input_tokens | 20 / 20 | 18 / 18 | +2 | +2 |
| output_tokens | 6437 / 6437 | 5925 / 5925 | +512 | +512 |
| cache_creation_input_tokens | 45331 / 45331 | 20995 / 20995 | +24336 | +24336 |
| cache_read_input_tokens | 290515 / 290515 | 298347 / 298347 | -7832 | -7832 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| gh-failure-fails-the-job | 1/1 | 1/1 |
| partial-listing-fails-the-job | 1/1 | 1/1 |
| empty-org-still-green | 1/1 | 1/1 |
| listed-repos-still-audited | 1/1 | 1/1 |
| allowlist-untouched | 1/1 | 1/1 |
