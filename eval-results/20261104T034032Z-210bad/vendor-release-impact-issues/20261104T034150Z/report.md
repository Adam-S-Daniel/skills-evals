# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T034150Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T034032Z-210bad; started 2026-11-04T03:41:50Z, ended 2026-11-04T03:43:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.89 to 0.9, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 4 call(s); agent $0.31, judge $0.17, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1883 / 0.1883 |
| without_skill | 1 | 0 | 4/5 | 5.5 (5.5 to 5.5, 1 judged) | 0.1251 / 0.1251 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1883 / 0.1883 | 0.1251 / 0.1251 | +0.0631 | +0.0631 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 34977 / 34977 | 20058 / 20058 | +14919 | +14919 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4369 / 4369 | 1926 / 1926 | +2443 | +2443 |
| cache_creation_input_tokens | 31789 / 31789 | 23429 / 23429 | +8360 | +8360 |
| cache_read_input_tokens | 173822 / 173822 | 121179 / 121179 | +52643 | +52643 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 1/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
