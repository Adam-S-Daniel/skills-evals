# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T160844Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T160506Z-554e96; started 2026-11-03T16:08:44Z, ended 2026-11-03T16:09:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.56, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1923 / 0.1923 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.1316 / 0.1316 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1923 / 0.1923 | 0.1316 / 0.1316 | +0.0606 | +0.0606 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 34248 / 34248 | 22583 / 22583 | +11665 | +11665 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 4371 / 4371 | 2415 / 2415 | +1956 | +1956 |
| cache_creation_input_tokens | 31630 / 31630 | 23839 / 23839 | +7791 | +7791 |
| cache_read_input_tokens | 219960 / 219960 | 121085 / 121085 | +98875 | +98875 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 0/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
