# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T122754Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T122607Z-be3d4f; started 2026-11-03T12:27:54Z, ended 2026-11-03T12:30:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.4, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 2 call(s); agent $0.89, judge $0.00, guard $0.00; last agent call $0.40

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.4889 / 0.4889 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.4023 / 0.4023 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4889 / 0.4889 | 0.4023 / 0.4023 | +0.0865 | +0.0865 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 98824 / 98824 | 57450 / 57450 | +41374 | +41374 |
| input_tokens | 20 / 20 | 14 / 14 | +6 | +6 |
| output_tokens | 6996 / 6996 | 6090 / 6090 | +906 | +906 |
| cache_creation_input_tokens | 34699 / 34699 | 28889 / 28889 | +5810 | +5810 |
| cache_read_input_tokens | 356304 / 356304 | 246878 / 246878 | +109426 | +109426 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 1/1 |
| titles-unstamped | 1/1 | 0/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
