# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T153722Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T152920Z-e19c35; started 2026-11-07T15:37:22Z, ended 2026-11-07T15:40:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.91, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/5 | skipped (objective-decided) | 0.1752 / 0.5257 |
| without_skill | 3 | 0 | 3/5 | skipped (objective-decided) | 0.1273 / 0.3818 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1752 / 0.1752 | 0.1273 / 0.1263 | +0.0480 | +0.0489 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 38821.7 / 38383 | 21970 / 21019 | +16851.7 | +17364 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 4102.7 / 4132 | 2096 / 2033 | +2006.7 | +2099 |
| cache_creation_input_tokens | 30312.7 / 30223 | 23545 / 23464 | +6767.7 | +6759 |
| cache_read_input_tokens | 129338 / 129398 | 121248.7 / 121192 | +8089.3 | +8206 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 3/3 | 0/3 |
| quoted-text-unstamped | 1/3 | 0/3 |
| titles-unstamped | 3/3 | 3/3 |
| prose-versions-stamped | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
