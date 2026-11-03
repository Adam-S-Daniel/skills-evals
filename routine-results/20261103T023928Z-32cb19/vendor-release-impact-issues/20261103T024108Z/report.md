# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T024108Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T023928Z-32cb19; started 2026-11-03T02:41:08Z, ended 2026-11-03T02:42:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1753 / 0.1753 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.1308 / 0.1308 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1753 / 0.1753 | 0.1308 / 0.1308 | +0.0445 | +0.0445 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 32527 / 32527 | 19465 / 19465 | +13062 | +13062 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3911 / 3911 | 2361 / 2361 | +1550 | +1550 |
| cache_creation_input_tokens | 30792 / 30792 | 23756 / 23756 | +7036 | +7036 |
| cache_read_input_tokens | 129569 / 129569 | 121198 / 121198 | +8371 | +8371 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 0/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
