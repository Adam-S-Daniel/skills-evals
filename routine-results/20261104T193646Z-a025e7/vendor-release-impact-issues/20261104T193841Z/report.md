# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T193841Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T193646Z-a025e7; started 2026-11-04T19:38:41Z, ended 2026-11-04T19:40:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 2 call(s); agent $0.30, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: stamps-skip-quotes (n=1)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.1795 / 0.1795 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.1233 / 0.1233 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1795 / 0.1795 | 0.1233 / 0.1233 | +0.0562 | +0.0562 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 41501 / 41501 | 26559 / 26559 | +14942 | +14942 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4065 / 4065 | 1888 / 1888 | +2177 | +2177 |
| cache_creation_input_tokens | 30357 / 30357 | 23083 / 23083 | +7274 | +7274 |
| cache_read_input_tokens | 173722 / 173722 | 120881 / 120881 | +52841 | +52841 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 1/1 | 0/1 |
| quoted-text-unstamped | 0/1 | 0/1 |
| titles-unstamped | 1/1 | 1/1 |
| prose-versions-stamped | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
